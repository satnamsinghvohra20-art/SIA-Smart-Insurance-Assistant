import json
import os
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "claims_db.json"

# Ensure directory exists
DB_DIR.mkdir(parents=True, exist_ok=True)

def _load_db() -> dict:
    if not DB_PATH.exists():
        return {}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_db(db_data: dict):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

def save_claim(claim_id: str, claim_data: dict):
    db = _load_db()
    db[claim_id] = claim_data
    _save_db(db)

def get_claim(claim_id: str) -> dict | None:
    db = _load_db()
    return db.get(claim_id)

def list_claims() -> list:
    db = _load_db()
    return list(db.values())
