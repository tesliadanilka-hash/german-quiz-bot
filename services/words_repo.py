from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config import WORDS_FILE
from services.state import TOPIC_ALL

Word = Dict[str, Any]

# ====== ХРАНИЛИЩЕ ======

WORDS: List[Word] = []
WORDS_BY_TOPIC: Dict[str, List[int]] = defaultdict(list)

LEVEL_COUNTS: Dict[str, int] = defaultdict(int)
TOPIC_COUNTS: Dict[Tuple[str, str], int] = defaultdict(int)
SUBTOPIC_COUNTS: Dict[Tuple[str, str, str], int] = defaultdict(int)

TOPIC_ID_BY_KEY: Dict[Tuple[str, str], str] = {}
TOPIC_KEY_BY_ID: Dict[str, Tuple[str, str]] = {}
SUBTOPIC_ID_BY_KEY: Dict[Tuple[str, str, str], str] = {}
SUBTOPIC_KEY_BY_ID: Dict[str, Tuple[str, str, str]] = {}


# ====== ЗАГРУЗКА ======

def load_words() -> None:
    global WORDS, WORDS_BY_TOPIC
    global LEVEL_COUNTS, TOPIC_COUNTS, SUBTOPIC_COUNTS
    global TOPIC_ID_BY_KEY, TOPIC_KEY_BY_ID, SUBTOPIC_ID_BY_KEY, SUBTOPIC_KEY_BY_ID

    WORDS.clear()
    WORDS_BY_TOPIC.clear()
    LEVEL_COUNTS.clear()
    TOPIC_COUNTS.clear()
    SUBTOPIC_COUNTS.clear()
    TOPIC_ID_BY_KEY.clear()
    TOPIC_KEY_BY_ID.clear()
    SUBTOPIC_ID_BY_KEY.clear()
    SUBTOPIC_KEY_BY_ID.clear()

    path = Path(WORDS_FILE)

    if not path.exists():
        print(f"[words_repo] words.json not found: {path}")
        return

    try:
        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            print("[words_repo] words.json is empty")
            return
        data = json.loads(raw_text)
    except Exception as e:
        print("[words_repo] Failed to parse words.json:", e)
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
        WORDS.append(
            {
                "id": idx,
                "de": de,
                "tr": tr,
                "ru": ru,
                "level": level,
                "topic": topic,
                "subtopic": subtopic,
            }
        )

        key_topic = f"{level}|{topic}"
        key_subtopic = f"{level}|{topic}|{subtopic}"

        WORDS_BY_TOPIC[TOPIC_ALL].append(idx)
        WORDS_BY_TOPIC[key_topic].append(idx)
        WORDS_BY_TOPIC[key_subtopic].append(idx)

        LEVEL_COUNTS[level] += 1
        TOPIC_COUNTS[(level, topic)] += 1
        SUBTOPIC_COUNTS[(level, topic, subtopic)] += 1

    # ====== ТВОЙ ФОРМАТ words.json ======
    # [
    #   { level, topic, subtopic, words: [ {de,tr,ru}, ... ] },
    #   ...
    # ]

    if isinstance(data, list):
        for block in data:
            if not isinstance(block, dict):
                continue
            level = block.get("level", "")
            topic = block.get("topic", "")
            subtopic = block.get("subtopic", "")
            for raw in block.get("words", []):
                if isinstance(raw, dict):
                    add_word(raw, level, topic, subtopic)

    elif isinstance(data, dict) and "topics" in data:
        for block in data["topics"]:
            level = block.get("level", "")
            topic = block.get("topic", "")
            subtopic = block.get("subtopic", "")
            for raw in block.get("words", []):
                if isinstance(raw, dict):
                    add_word(raw, level, topic, subtopic)

    else:
        print("[words_repo] Unknown format of words.json")
        return

    # ====== ID МАППИНГ ======

    for i, key in enumerate(sorted(TOPIC_COUNTS.keys())):
        TOPIC_ID_BY_KEY[key] = f"t{i}"
        TOPIC_KEY_BY_ID[f"t{i}"] = key

    for i, key in enumerate(sorted(SUBTOPIC_COUNTS.keys())):
        SUBTOPIC_ID_BY_KEY[key] = f"s{i}"
        SUBTOPIC_KEY_BY_ID[f"s{i}"] = key

    print(
        f"[words_repo] Loaded {len(WORDS)} words | "
        f"Topics: {len(TOPIC_COUNTS)} | "
        f"Subtopics: {len(SUBTOPIC_COUNTS)}"
    )


# ====== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ======

def get_levels() -> List[str]:
    return sorted(LEVEL_COUNTS.keys())


def get_topics_for_level(level: str) -> List[str]:
    return sorted({topic for (lvl, topic), cnt in TOPIC_COUNTS.items() if lvl == level and cnt > 0})


def get_subtopics_for_level_topic(level: str, topic: str) -> List[str]:
    return sorted({
        sub for (lvl, top, sub), cnt in SUBTOPIC_COUNTS.items()
        if lvl == level and top == topic and cnt > 0
    })


def get_word_ids_for_topic(topic_key: str) -> List[int]:
    if topic_key == TOPIC_ALL:
        return WORDS_BY_TOPIC.get(TOPIC_ALL, [])
    return WORDS_BY_TOPIC.get(topic_key, [])


def pretty_topic_name(topic_key: str) -> str:
    if not topic_key or topic_key == TOPIC_ALL:
        return "Все слова"

    parts = topic_key.split("|")
    if len(parts) == 2:
        level, topic = parts
        return f"Уровень {level}: {topic}"
    if len(parts) == 3:
        level, topic, sub = parts
        return f"Уровень {level}: {topic} → {sub}"
    return topic_key


def new_shuffled_cycle(topic_key: str) -> List[int]:
    ids = get_word_ids_for_topic(topic_key).copy()
    random.shuffle(ids)
    return ids
