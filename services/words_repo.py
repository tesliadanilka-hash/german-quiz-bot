from __future__ import annotations

import json
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from config import WORDS_FILE
from services.state import TOPIC_ALL

Word = Dict[str, Any]

WORDS: List[Word] = []
WORDS_BY_TOPIC: dict[str, list[int]] = defaultdict(list)
LEVEL_COUNTS: dict[str, int] = defaultdict(int)
TOPIC_COUNTS: dict[Tuple[str, str], int] = defaultdict(int)
SUBTOPIC_COUNTS: dict[Tuple[str, str, str], int] = defaultdict(int)

TOPIC_ID_BY_KEY: dict[Tuple[str, str], str] = {}
TOPIC_KEY_BY_ID: dict[str, Tuple[str, str]] = {}
SUBTOPIC_ID_BY_KEY: dict[Tuple[str, str, str], str] = {}
SUBTOPIC_KEY_BY_ID: dict[str, Tuple[str, str, str]] = {}

def load_words() -> None:
    global WORDS, WORDS_BY_TOPIC, LEVEL_COUNTS, TOPIC_COUNTS, SUBTOPIC_COUNTS
    global TOPIC_ID_BY_KEY, TOPIC_KEY_BY_ID, SUBTOPIC_ID_BY_KEY, SUBTOPIC_KEY_BY_ID

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)
    LEVEL_COUNTS = defaultdict(int)
    TOPIC_COUNTS = defaultdict(int)
    SUBTOPIC_COUNTS = defaultdict(int)
    TOPIC_ID_BY_KEY = {}
    TOPIC_KEY_BY_ID = {}
    SUBTOPIC_ID_BY_KEY = {}
    SUBTOPIC_KEY_BY_ID = {}

    if not WORDS_FILE.exists():
        print(f"Words file not found: {WORDS_FILE}")
        return

    try:
        raw_text = WORDS_FILE.read_text(encoding="utf-8").strip()
        if not raw_text:
            print(f"Words file is empty: {WORDS_FILE}")
            return
        data = json.loads(raw_text)
    except Exception as e:
        print("Failed to parse words.json:", e)
        return

    def add_word(raw: Dict[str, Any], level_raw: str, topic_raw: str, subtopic_raw: str) -> None:
        de = raw.get("de")
        tr = raw.get("tr")
        ru = raw.get("ru")
        if not de or not tr or not ru:
            return

        level = (level_raw or "").strip() or "A1"
        topic = (topic_raw or "").strip() or "Без темы"
        subtopic = (subtopic_raw or "").strip() or "Общее"

        idx = len(WORDS)
        word: Word = {
            "id": idx,
            "de": de,
            "tr": tr,
            "ru": ru,
            "level": level,
            "topic": topic,
            "subtopic": subtopic,
        }
        WORDS.append(word)

        key_all = TOPIC_ALL
        key_topic = f"{level}|{topic}"
        key_subtopic = f"{level}|{topic}|{subtopic}"

        WORDS_BY_TOPIC[key_all].append(idx)
        WORDS_BY_TOPIC[key_topic].append(idx)
        WORDS_BY_TOPIC[key_subtopic].append(idx)

        LEVEL_COUNTS[level] += 1
        TOPIC_COUNTS[(level, topic)] += 1
        SUBTOPIC_COUNTS[(level, topic, subtopic)] += 1

    # Поддержка формата как у тебя: list блоков с "words"
    if isinstance(data, list):
        for block in data:
            if isinstance(block, dict) and "words" in block:
                level_raw = block.get("level") or ""
                topic_raw = block.get("topic") or ""
                subtopic_raw = block.get("subtopic") or ""
                for w in block.get("words", []):
                    if isinstance(w, dict):
                        add_word(w, level_raw, topic_raw, subtopic_raw)
            elif isinstance(block, dict):
                add_word(block, block.get("level") or "", block.get("topic") or "", block.get("subtopic") or "")
    elif isinstance(data, dict) and "topics" in data:
        for block in data["topics"]:
            level_raw = block.get("level") or ""
            topic_raw = block.get("topic") or ""
            subtopic_raw = block.get("subtopic") or ""
            for w in block.get("words", []):
                if isinstance(w, dict):
                    add_word(w, level_raw, topic_raw, subtopic_raw)
    else:
        print("Unknown words.json format.")
        return

    for i, key in enumerate(sorted(TOPIC_COUNTS.keys())):
        tid = f"t{i}"
        TOPIC_ID_BY_KEY[key] = tid
        TOPIC_KEY_BY_ID[tid] = key

    for i, key in enumerate(sorted(SUBTOPIC_COUNTS.keys())):
        sid = f"s{i}"
        SUBTOPIC_ID_BY_KEY[key] = sid
        SUBTOPIC_KEY_BY_ID[sid] = key

    print(f"Words loaded: {len(WORDS)}. Topics: {len(TOPIC_COUNTS)}. Subtopics: {len(SUBTOPIC_COUNTS)}")

def get_levels() -> List[str]:
    return sorted(LEVEL_COUNTS.keys())

def get_topics_for_level(level: str) -> List[str]:
    return sorted({topic for (lvl, topic), cnt in TOPIC_COUNTS.items() if lvl == level and cnt > 0})

def get_subtopics_for_level_topic(level: str, topic: str) -> List[str]:
    return sorted({sub for (lvl, top, sub), cnt in SUBTOPIC_COUNTS.items() if lvl == level and top == topic and cnt > 0})

def get_ids_for_topic_key(topic_key: str) -> List[int]:
    if topic_key not in WORDS_BY_TOPIC or topic_key == TOPIC_ALL:
        return WORDS_BY_TOPIC.get(TOPIC_ALL, [])
    return WORDS_BY_TOPIC[topic_key]

def reset_remaining_for_topic(topic_key: str) -> List[int]:
    ids = list(get_ids_for_topic_key(topic_key))
    random.shuffle(ids)
    return ids
