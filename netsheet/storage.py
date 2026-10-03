"""Where net sheets are kept on the Mac.

Default location:  ~/Documents/Seller Net Sheets/
One folder per property, for example:

  Seller Net Sheets/
    123 Main St Forest City/
      net-sheet-data.json           current figures + where each came from
      audit-log.jsonl               append-only history of every change
      Purchase Agreement (copy).pdf read-only COPY; the original is never touched
      Generated Net Sheets/
        v001 2026-10-03 1415 Client Net Sheet.pdf
        v001 2026-10-03 1415 data snapshot.json
        v002 ...

Safety rules enforced here:
  * Generated PDFs and snapshots are created with "exclusive create" — if a
    file with that name already exists, the write fails instead of replacing it.
  * Folders are never renamed, moved or deleted by this app.
  * The contract copy is made read-only and fingerprinted (SHA-256) so you can
    prove it is identical to what was uploaded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from . import models

DATA_FILE = "net-sheet-data.json"
AUDIT_FILE = "audit-log.jsonl"
OUTPUT_DIR = "Generated Net Sheets"
CONTRACT_NAME = "Purchase Agreement (copy).pdf"


def data_root() -> Path:
    override = os.environ.get("NETSHEET_DATA_DIR")
    root = Path(override) if override else Path.home() / "Documents" / "Seller Net Sheets"
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_folder_name(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9 ,.#&'()-]", " ", name or "")
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:80] or "Untitled net sheet"


def tx_dir(tx_id: str) -> Path:
    """Look up an existing transaction folder. Only names that actually exist
    directly inside the data folder are accepted."""
    root = data_root()
    for child in root.iterdir():
        if child.is_dir() and child.name == tx_id and (child / DATA_FILE).exists():
            return child
    raise FileNotFoundError(tx_id)


def list_transactions() -> list[dict]:
    out = []
    for child in sorted(data_root().iterdir()):
        f = child / DATA_FILE
        if child.is_dir() and f.exists():
            try:
                out.append(json.loads(f.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
    out.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    return out


def create_transaction(mode: str, name: str) -> dict:
    root = data_root()
    base = safe_folder_name(name)
    candidate, n = base, 2
    while (root / candidate).exists():
        candidate = f"{base} ({n})"
        n += 1
    folder = root / candidate
    folder.mkdir()
    (folder / OUTPUT_DIR).mkdir()
    tx = models.new_transaction(mode, candidate)
    if mode == "listing" or name:
        tx["facts"]["property_address"]["value"] = name.strip()
    _write_json(folder / DATA_FILE, tx)
    audit(candidate, "created", {"mode": mode, "name": name})
    return tx


def load(tx_id: str) -> dict:
    return json.loads((tx_dir(tx_id) / DATA_FILE).read_text())


def save(tx: dict, changes: list[dict] | None = None) -> None:
    tx["updated_at"] = models.now_iso()
    folder = tx_dir(tx["id"])
    _write_json(folder / DATA_FILE, tx)
    if changes:
        audit(tx["id"], "edited", {"changes": changes})


def audit(tx_id: str, action: str, details: dict) -> None:
    entry = {"at": models.now_iso(), "action": action, **details}
    with open(tx_dir(tx_id) / AUDIT_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def read_audit(tx_id: str) -> list[dict]:
    path = tx_dir(tx_id) / AUDIT_FILE
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def store_contract_copy(tx: dict, original_filename: str, data: bytes) -> dict:
    """Save a read-only copy of an uploaded Purchase Agreement.
    The original file on the Mac is never opened for writing by this app."""
    if not data.startswith(b"%PDF"):
        raise ValueError("That file does not appear to be a PDF.")
    folder = tx_dir(tx["id"])
    target = folder / CONTRACT_NAME
    n = 2
    while target.exists():  # a second upload never replaces the first copy
        target = folder / f"Purchase Agreement (copy {n}).pdf"
        n += 1
    with open(target, "xb") as fh:
        fh.write(data)
    os.chmod(target, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    info = {
        "stored_as": target.name,
        "original_filename": original_filename,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "uploaded_at": models.now_iso(),
    }
    tx["contract_file"] = info
    tx.setdefault("contract_history", []).append(info)
    save(tx)
    audit(tx["id"], "contract_copy_stored", info)
    return info


def next_version(tx_id: str) -> int:
    out = tx_dir(tx_id) / OUTPUT_DIR
    out.mkdir(exist_ok=True)
    nums = [int(m.group(1)) for p in out.iterdir() if (m := re.match(r"v(\d{3,})\b", p.name))]
    return max(nums, default=0) + 1


def write_version(tx: dict, view: str, pdf_bytes: bytes) -> Path:
    """Save a new numbered PDF and a matching data snapshot. Never overwrites."""
    folder = tx_dir(tx["id"]) / OUTPUT_DIR
    folder.mkdir(exist_ok=True)
    version = next_version(tx["id"])
    stamp = models.now_iso().replace("T", " ")[:16].replace(":", "")
    label = "Client Net Sheet" if view == "client" else "Agent Worksheet"
    pdf_path = folder / f"v{version:03d} {stamp} {label}.pdf"
    snap_path = folder / f"v{version:03d} {stamp} data snapshot.json"
    with open(pdf_path, "xb") as fh:
        fh.write(pdf_bytes)
    with open(snap_path, "x", encoding="utf-8") as fh:
        json.dump(tx, fh, indent=2)
    audit(tx["id"], "pdf_generated", {"version": version, "view": view, "file": pdf_path.name})
    return pdf_path


def list_outputs(tx_id: str) -> list[str]:
    folder = tx_dir(tx_id) / OUTPUT_DIR
    if not folder.exists():
        return []
    return sorted((p.name for p in folder.iterdir() if p.suffix == ".pdf"), reverse=True)


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)  # atomic swap so a crash can't leave a half-written file
