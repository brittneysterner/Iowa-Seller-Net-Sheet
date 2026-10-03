"""The local web app. Runs only on this Mac (127.0.0.1) — not reachable from the internet."""

from __future__ import annotations

from decimal import Decimal

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from .. import models, storage
from ..calculations.commission import METHODS
from ..calculations.net_proceeds import SECTIONS, compute
from ..money import MoneyError, fmt, parse_money
from ..pdf_output import CLIENT_DISCLAIMER, LISTING_NOTE, build_pdf

app = Flask(__name__)
app.secret_key = "local-only"  # only used for on-screen messages; the app is not on the internet
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024


@app.template_filter("usdate")
def usdate(text):
    try:
        d = models.parse_date(text)
    except ValueError:
        return text
    return d.strftime("%m/%d/%Y") if d else ""


@app.context_processor
def helpers():
    return {
        "fmt": fmt, "models": models, "METHODS": METHODS, "SECTIONS": SECTIONS,
        "CLIENT_DISCLAIMER": CLIENT_DISCLAIMER, "LISTING_NOTE": LISTING_NOTE,
    }


def _load_or_404(tx_id: str) -> dict:
    try:
        return storage.load(tx_id)
    except FileNotFoundError:
        abort(404)


@app.get("/")
def index():
    return render_template("index.html", transactions=storage.list_transactions(), root=storage.data_root())


@app.post("/new")
def new():
    mode = request.form.get("mode", "listing")
    name = request.form.get("name", "").strip()
    if not name:
        flash("Please type the property address (or a name) for this net sheet.")
        return redirect(url_for("index"))
    tx = storage.create_transaction(mode, name)
    return redirect(url_for("edit", tx_id=tx["id"]))


@app.get("/t/<tx_id>")
def edit(tx_id):
    tx = _load_or_404(tx_id)
    sheet = compute(tx)
    return render_template("edit.html", tx=tx, sheet=sheet, outputs=storage.list_outputs(tx_id),
                           cost_suggestions=models.OTHER_COST_SUGGESTIONS,
                           credit_suggestions=models.CREDIT_SUGGESTIONS)


# ---------------------------------------------------------------- saving the form
def _rows(form, prefix: str, fields: list[str]) -> list[dict]:
    rows = []
    for rid in form.getlist(f"{prefix}-id"):
        if not rid.isalnum():
            continue
        row = {"id": rid}
        for f in fields:
            row[f] = form.get(f"{prefix}-{rid}-{f}", "").strip()
        rows.append(row)
    return rows


def _diff(changes: list, path: str, old, new):
    if old != new:
        changes.append({"field": path, "from": old, "to": new})


def apply_form(tx: dict, form) -> tuple[list[dict], list[str]]:
    changes: list[dict] = []
    problems: list[str] = []

    for key, (label, kind) in models.FACTS.items():
        field = f"fact-{key}"
        if field not in form:
            continue
        new_val = form.get(field, "").strip()
        if kind == "money" and new_val:
            try:
                parsed = parse_money(new_val)
                new_val = str(parsed)
            except MoneyError as exc:
                problems.append(f"{label}: {exc}. Not saved.")
                continue
        if kind == "date" and new_val:
            try:
                new_val = models.parse_date(new_val).isoformat()
            except ValueError as exc:
                problems.append(f"{label}: {exc}. Not saved.")
                continue
        fact = tx["facts"][key]
        if fact.get("source") == "contract":
            if new_val != fact.get("value"):
                # Agent corrected a contract suggestion: keep the original for the audit trail.
                fact["original_suggestion"] = {k: fact.get(k) for k in ("value", "page", "quote", "provider")}
                fact["source"] = "manual"
                fact["confirmed"] = True
                fact["note"] = "Corrected by agent"
            else:
                was = fact.get("confirmed", False)
                fact["confirmed"] = form.get(f"{field}-confirmed") == "on"
                _diff(changes, f"facts.{key}.confirmed", was, fact["confirmed"])
        _diff(changes, f"facts.{key}", fact.get("value"), new_val)
        if fact.get("value") != new_val:
            fact["updated_at"] = models.now_iso()
        fact["value"] = new_val

    if "seller_paid_buyer_costs_status" in form:
        new = form.get("seller_paid_buyer_costs_status")
        _diff(changes, "seller_paid_buyer_costs_status", tx.get("seller_paid_buyer_costs_status"), new)
        tx["seller_paid_buyer_costs_status"] = new

    def replace_list(name, new_rows):
        _diff(changes, name, tx.get(name), new_rows)
        tx[name] = new_rows

    if "commissions-present" in form:
        replace_list("commissions", _rows(form, "commissions", ["role", "label", "method", "percent", "flat", "status", "payee", "notes"]))
    if "payoffs-present" in form:
        replace_list("payoffs", _rows(form, "payoffs", ["lender", "amount", "good_through", "per_diem", "status", "notes"]))
    if "other-present" in form:
        replace_list("other_costs", _rows(form, "other", ["label", "amount", "status", "provider", "notes"]))
    if "credits-present" in form:
        replace_list("credits", _rows(form, "credits", ["label", "amount", "status", "notes"]))

    if "ptax-present" in form:
        pt = dict(tx["property_tax"])
        for f in ("county", "parcel", "annual_net_tax", "tax_source", "tax_retrieved", "notes"):
            pt[f] = form.get(f"ptax-{f}", "").strip()
        pt["lines"] = _rows(form, "ptaxline", ["label", "amount", "kind", "status", "notes"])
        _diff(changes, "property_tax", tx["property_tax"], pt)
        tx["property_tax"] = pt

    if "tt-present" in form:
        tt = {
            "include": form.get("tt-include") == "on",
            "personal_property_flag": form.get("tt-personal_property_flag") == "on",
            "exemption_flag": form.get("tt-exemption_flag") == "on",
            "actual_amount": form.get("tt-actual_amount", "").strip(),
            "notes": form.get("tt-notes", "").strip(),
        }
        _diff(changes, "transfer_tax", tx["transfer_tax"], tt)
        tx["transfer_tax"] = tt

    for key in ("abstract", "deed_prep"):
        if f"{key}-present" in form:
            item = {f: form.get(f"{key}-{f}", "").strip() for f in ("amount", "status", "provider", "notes")}
            _diff(changes, key, tx[key], item)
            tx[key] = item

    if "review-present" in form:
        for item in tx["review_items"]:
            rid = item["id"]
            resolved = form.get(f"review-{rid}-resolved") == "on"
            resolution = form.get(f"review-{rid}-resolution", "").strip()
            _diff(changes, f"review_items.{rid}", {"resolved": item.get("resolved"), "resolution": item.get("resolution")},
                  {"resolved": resolved, "resolution": resolution})
            item["resolved"], item["resolution"] = resolved, resolution
        new_text = form.get("review-new-text", "").strip()
        if new_text:
            item = {"id": models.new_id(), "text": new_text, "page": None,
                    "quote": form.get("review-new-quote", "").strip() or None,
                    "source": "manual", "resolved": False, "resolution": ""}
            tx["review_items"].append(item)
            changes.append({"field": "review_items", "added": item})

    # Validate money fields in rows so problems are visible right away (values are kept as typed).
    sheet = compute(tx)
    problems.extend(e for e in sheet.input_errors if e not in problems)
    return changes, problems


@app.post("/t/<tx_id>/save")
def save(tx_id):
    tx = _load_or_404(tx_id)
    changes, problems = apply_form(tx, request.form)
    storage.save(tx, changes)
    for p in problems:
        flash("Please fix: " + p)
    if not problems:
        flash("Saved.")
    target = request.form.get("next", "edit")
    if target == "results":
        return redirect(url_for("results", tx_id=tx_id, view=request.form.get("view", "agent")))
    anchor = request.form.get("anchor", "")
    return redirect(url_for("edit", tx_id=tx_id) + (f"#{anchor}" if anchor.isidentifier() else ""))


@app.post("/t/<tx_id>/contract")
def upload_contract(tx_id):
    tx = _load_or_404(tx_id)
    f = request.files.get("contract")
    if not f or not f.filename:
        flash("Choose a PDF file first.")
        return redirect(url_for("edit", tx_id=tx_id))
    try:
        storage.store_contract_copy(tx, f.filename, f.read())
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("edit", tx_id=tx_id))
    flash("A read-only copy of the Purchase Agreement was saved. Your original file was not changed.")
    return redirect(url_for("edit", tx_id=tx_id) + "#facts")


@app.get("/t/<tx_id>/contract.pdf")
def contract_pdf(tx_id):
    tx = _load_or_404(tx_id)
    if not tx.get("contract_file"):
        abort(404)
    return send_file(storage.tx_dir(tx_id) / tx["contract_file"]["stored_as"], mimetype="application/pdf")


@app.get("/t/<tx_id>/results")
def results(tx_id):
    tx = _load_or_404(tx_id)
    view = "client" if request.args.get("view") == "client" else "agent"
    return render_template("results.html", tx=tx, sheet=compute(tx), view=view, outputs=storage.list_outputs(tx_id))


@app.post("/t/<tx_id>/pdf")
def make_pdf(tx_id):
    tx = _load_or_404(tx_id)
    view = "client" if request.form.get("view") == "client" else "agent"
    sheet = compute(tx)
    if sheet.price is None:
        flash("Enter a sale price before creating a PDF.")
        return redirect(url_for("results", tx_id=tx_id, view=view))
    path = storage.write_version(tx, view, build_pdf(sheet, view))
    flash(f"Created {path.name}. Earlier versions were kept.")
    return redirect(url_for("results", tx_id=tx_id, view=view))


@app.get("/t/<tx_id>/files/<path:name>")
def output_file(tx_id, name):
    _load_or_404(tx_id)
    if name not in storage.list_outputs(tx_id):
        abort(404)
    return send_file(storage.tx_dir(tx_id) / storage.OUTPUT_DIR / name, mimetype="application/pdf")


@app.route("/t/<tx_id>/compare", methods=["GET", "POST"])
def compare(tx_id):
    tx = _load_or_404(tx_id)
    sheet = compute(tx)
    problems = []
    if request.method == "POST":
        amounts = {}
        for ln in sheet.lines:
            raw = request.form.get(f"settle-{ln.key}", "").strip()
            if raw:
                try:
                    amounts[ln.key] = str(parse_money(raw))
                except MoneyError as exc:
                    problems.append(f"{ln.label}: {exc}")
        comp = {
            "line_amounts": amounts,
            "settlement_net": request.form.get("settlement_net", "").strip(),
            "notes": request.form.get("notes", "").strip(),
        }
        change = [{"field": "comparison", "from": tx.get("comparison"), "to": comp}]
        tx["comparison"] = comp
        storage.save(tx, change)
        for p in problems:
            flash("Please fix: " + p)
        return redirect(url_for("compare", tx_id=tx_id))

    comp = tx.get("comparison") or {}
    rows = []
    for ln in sheet.lines:
        raw = comp.get("line_amounts", {}).get(ln.key, "")
        settled = Decimal(raw) if raw else None
        diff = None if settled is None or ln.amount is None else settled - ln.amount
        rows.append({"line": ln, "settled": raw, "diff": diff})
    try:
        settle_net = parse_money(comp.get("settlement_net"))
    except MoneyError:
        settle_net = None
    net_diff = None if settle_net is None or sheet.net is None else settle_net - sheet.net
    return render_template("compare.html", tx=tx, sheet=sheet, rows=rows, comp=comp,
                           settle_net=settle_net, net_diff=net_diff)


@app.get("/t/<tx_id>/history")
def history(tx_id):
    tx = _load_or_404(tx_id)
    return render_template("history.html", tx=tx, entries=list(reversed(storage.read_audit(tx_id))))
