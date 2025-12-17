import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import GRAMMAR_FILE

GRAMMAR_RULES: List[Dict[str, Any]] = []

def load_grammar_rules(path: Optional[Path] = None) -> None:
    global GRAMMAR_RULES
    file_path = Path(path) if path else Path(GRAMMAR_FILE)

    print(f"[grammar_repo] GRAMMAR_FILE = {file_path}")
    print(f"[grammar_repo] exists = {file_path.exists()}")

    if not file_path.exists():
        GRAMMAR_RULES = []
        print("[grammar_repo] grammar.json not found. 0 rules loaded.")
        return

    try:
        print(f"[grammar_repo] size = {file_path.stat().st_size} bytes")
    except Exception:
        pass

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        GRAMMAR_RULES = []
        print("[grammar_repo] JSON load error:", e)
        return

    if isinstance(data, list):
        GRAMMAR_RULES = data
    elif isinstance(data, dict) and "rules" in data and isinstance(data["rules"], list):
        GRAMMAR_RULES = data["rules"]
    else:
        GRAMMAR_RULES = []

    print(f"[grammar_repo] Loaded rules: {len(GRAMMAR_RULES)}")

def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    for r in GRAMMAR_RULES:
        if str(r.get("id")) == str(rule_id):
            return r
    return None
