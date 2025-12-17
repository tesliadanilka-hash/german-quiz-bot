from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import GRAMMAR_FILE

GRAMMAR_RULES: List[Dict[str, Any]] = []


def strip_html_tags(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    for tag in ("<b>", "</b>", "<i>", "</i>", "<u>", "</u>"):
        text = text.replace(tag, "")
    return text


def load_grammar_rules() -> None:
    global GRAMMAR_RULES
    file_path = Path(GRAMMAR_FILE)
    if not file_path.exists():
        GRAMMAR_RULES = []
        print(f"Grammar file not found: {file_path}")
        return

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        GRAMMAR_RULES = []
        print(f"Failed to parse grammar.json: {e}")
        return

    if isinstance(data, list):
        GRAMMAR_RULES = data
    elif isinstance(data, dict) and "rules" in data and isinstance(data["rules"], list):
        GRAMMAR_RULES = data["rules"]
    elif isinstance(data, dict):
        rules: List[Dict[str, Any]] = []
        for v in data.values():
            if isinstance(v, list):
                rules.extend([x for x in v if isinstance(x, dict)])
        GRAMMAR_RULES = rules
    else:
        GRAMMAR_RULES = []

    print(f"Grammar rules loaded: {len(GRAMMAR_RULES)}")


def get_sublevel_from_topic(topic: str) -> str:
    if "—" in topic:
        return topic.split("—", 1)[0].strip()
    if "-" in topic:
        return topic.split("-", 1)[0].strip()
    return topic.strip()


def get_rules_by_level(level: str) -> List[Dict[str, Any]]:
    return [r for r in GRAMMAR_RULES if r.get("level") == level]


def get_sublevels_for_level(level: str) -> List[str]:
    sublevels = set()
    for rule in get_rules_by_level(level):
        topic = rule.get("topic", "")
        sub = get_sublevel_from_topic(topic)
        if sub.startswith(level):
            sublevels.add(sub)
    return sorted(sublevels)


def get_rules_by_sublevel(sublevel: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for r in GRAMMAR_RULES:
        topic = r.get("topic", "")
        if get_sublevel_from_topic(topic) == sublevel:
            result.append(r)
    return result


def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    for r in GRAMMAR_RULES:
        if str(r.get("id")) == str(rule_id):
            return r
    return None
