import hashlib
import json
import os
import stat

import pytest

from netsheet import storage
from netsheet.calculations.net_proceeds import compute
from netsheet.extraction.base import ExtractionResult, ReviewFlag, Suggestion, apply_suggestions
from netsheet.pdf_output import build_pdf

PDF = b"%PDF-1.4\n% fake test pdf\n"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NETSHEET_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client():
    from netsheet.web.app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_folders_never_collide(data_dir):
    a = storage.create_transaction("listing", "123 Main St")
    b = storage.create_transaction("listing", "123 Main St")
    assert a["id"] == "123 Main St" and b["id"] == "123 Main St (2)"


def test_folder_name_is_sanitized(data_dir):
    t = storage.create_transaction("listing", "../../etc/passwd")
    assert "/" not in t["id"] and (data_dir / t["id"]).parent == data_dir


def test_versions_never_overwrite(data_dir):
    tx = storage.create_transaction("listing", "A")
    p1 = storage.write_version(tx, "client", b"%PDF one")
    p2 = storage.write_version(tx, "client", b"%PDF two")
    assert p1 != p2 and p1.read_bytes() == b"%PDF one"
    assert p1.name.startswith("v001") and p2.name.startswith("v002")


def test_contract_copy_is_read_only_and_fingerprinted(data_dir):
    tx = storage.create_transaction("contract", "B")
    info = storage.store_contract_copy(tx, "PA.pdf", PDF)
    path = data_dir / "B" / info["stored_as"]
    assert path.read_bytes() == PDF
    assert info["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert not (path.stat().st_mode & stat.S_IWUSR)
    info2 = storage.store_contract_copy(storage.load("B"), "PA.pdf", PDF)
    assert info2["stored_as"] != info["stored_as"]  # second upload doesn't replace the first


def test_non_pdf_rejected(data_dir):
    tx = storage.create_transaction("contract", "C")
    with pytest.raises(ValueError):
        storage.store_contract_copy(tx, "x.pdf", b"not a pdf")


def test_suggestions_are_unconfirmed_and_never_replace_agent_values(data_dir):
    tx = storage.create_transaction("contract", "D")
    tx["facts"]["sellers"]["value"] = "Jane Doe"
    result = ExtractionResult(
        provider="test",
        suggestions=[
            Suggestion("sale_price", "250000", 1, "Purchase price: $250,000"),
            Suggestion("sellers", "John Doe", 1, "Seller: John Doe"),
        ],
        review_flags=[ReviewFlag("Seller to credit $2,000 for roof", 3, "Seller shall credit...")],
    )
    apply_suggestions(tx, result)
    assert tx["facts"]["sale_price"]["confirmed"] is False
    assert tx["facts"]["sale_price"]["quote"] == "Purchase price: $250,000"
    assert tx["facts"]["sellers"]["value"] == "Jane Doe"  # agent's value kept
    assert len(tx["review_items"]) == 2
    s = compute(tx)
    assert any("NEEDS REVIEW" in w for w in s.warnings)


def test_pdfs_build(data_dir):
    tx = storage.create_transaction("listing", "E")
    tx["facts"]["sale_price"]["value"] = "300000"
    tx["abstract"]["amount"] = "450"
    s = compute(tx)
    for view in ("client", "agent"):
        assert build_pdf(s, view).startswith(b"%PDF")


def test_web_flow(client, data_dir):
    r = client.post("/new", data={"mode": "contract", "name": "9 Elm St"})
    assert r.status_code == 302
    tx_id = "9 Elm St"
    assert client.get(f"/t/{tx_id}").status_code == 200

    form = {
        "fact-sale_price": "$250,000", "fact-closing_date": "2026-10-30", "fact-sellers": "Pat Seller",
        "commissions-present": "1", "commissions-id": "k1",
        "commissions-k1-role": "listing", "commissions-k1-method": "percent", "commissions-k1-percent": "3",
        "commissions-k1-status": "estimated",
        "abstract-present": "1", "abstract-amount": "450", "abstract-status": "estimated", "abstract-provider": "Abs Co",
        "tt-present": "1", "tt-include": "on",
    }
    r = client.post(f"/t/{tx_id}/save", data=form)
    assert r.status_code == 302
    tx = storage.load(tx_id)
    assert tx["facts"]["sale_price"]["value"] == "250000"
    assert tx["commissions"][0]["percent"] == "3"

    # bad money is reported, not saved silently
    r = client.post(f"/t/{tx_id}/save", data={"fact-sale_price": "two hundred"}, follow_redirects=True)
    assert b"Please fix" in r.data
    assert storage.load(tx_id)["facts"]["sale_price"]["value"] == "250000"

    for view in ("agent", "client"):
        page = client.get(f"/t/{tx_id}/results?view={view}")
        assert page.status_code == 200 and b"ESTIMATED NET PROCEEDS" in page.data
    agent = client.get(f"/t/{tx_id}/results?view=agent").data
    assert b"428A.1" in agent and b"NOT calculated" in agent
    client_view = client.get(f"/t/{tx_id}/results?view=client").data
    assert b"428A.1" not in client_view  # no technical clutter for the client

    client.post(f"/t/{tx_id}/pdf", data={"view": "client"})
    client.post(f"/t/{tx_id}/pdf", data={"view": "client"})
    outputs = storage.list_outputs(tx_id)
    assert len(outputs) == 2
    assert client.get(f"/t/{tx_id}/files/{outputs[0]}").status_code == 200
    assert client.get(f"/t/{tx_id}/files/..%2Fnet-sheet-data.json").status_code == 404

    r = client.post(f"/t/{tx_id}/compare", data={"settle-abstract": "475", "settlement_net": "100"})
    assert r.status_code == 302
    page = client.get(f"/t/{tx_id}/compare").data
    assert b"$25.00" in page

    log = storage.read_audit(tx_id)
    actions = [e["action"] for e in log]
    assert actions.count("pdf_generated") == 2 and "created" in actions and "edited" in actions
    assert client.get(f"/t/{tx_id}/history").status_code == 200


def test_listing_mode_pages(client):
    client.post("/new", data={"mode": "listing", "name": "Lake Home"})
    page = client.get("/t/Lake Home").data
    assert b"Hypothetical sale price" in page
    assert b"Upload PDF" not in page


def test_contract_upload_and_view(client, data_dir):
    client.post("/new", data={"mode": "contract", "name": "F"})
    import io
    r = client.post("/t/F/contract", data={"contract": (io.BytesIO(PDF), "Signed PA.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    assert client.get("/t/F/contract.pdf").data == PDF


def test_unknown_transaction_404(client):
    assert client.get("/t/nope").status_code == 404


def test_adobe_only_form_is_detected_and_warned(client, data_dir):
    import io
    client.post("/new", data={"mode": "contract", "name": "G"})
    xfa = b"%PDF-1.7\n1 0 obj << /AcroForm << /XFA [ (template) 4 0 R ] >> >>\n"
    client.post("/t/G/contract", data={"contract": (io.BytesIO(xfa), "blank form.pdf")},
                content_type="multipart/form-data")
    assert storage.load("G")["contract_file"]["adobe_only_form"] is True
    page = client.get("/t/G").data
    assert b"Adobe-only fillable form" in page
    assert b"POSSESSION date" in page  # form-based hint shown in contract mode


def test_old_records_gain_new_fields(data_dir):
    t = storage.create_transaction("contract", "Old")
    path = data_dir / "Old" / storage.DATA_FILE
    raw = json.loads(path.read_text())
    del raw["facts"]["settlement_agent"]
    path.write_text(json.dumps(raw))
    assert storage.load("Old")["facts"]["settlement_agent"]["value"] == ""


def test_settlement_agent_saved_and_shown(client):
    client.post("/new", data={"mode": "contract", "name": "H"})
    client.post("/t/H/save", data={"fact-settlement_agent": "Escrow Plus", "fact-sale_price": "100000"})
    assert storage.load("H")["facts"]["settlement_agent"]["value"] == "Escrow Plus"
    assert b"Escrow Plus" in client.get("/t/H/results?view=agent").data
    assert b"Escrow Plus" not in client.get("/t/H/results?view=client").data
