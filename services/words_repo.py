import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from config import WORDS_FILE

TOPIC_ALL = "ALL"

WORDS: List[Dict[str, Any]] = []
WORDS_BY_TOPIC: Dict[str, List[int]] = defaultdict(list)

LEVEL_COUNTS: Dict[str, int] = defaultdict(int)
TOPIC_COUNTS: Dict[Tuple[str, str], int] = defaultdict(int)
SUBTOPIC_COUNTS: Dict[Tuple[str, str, str], int] = defaultdict(int)

TOPIC_ID_BY_KEY: Dict[Tuple[str, str], str] = {}
TOPIC_KEY_BY_ID: Dict[str, Tuple[str, str]] = {}
SUBTOPIC_ID_BY_KEY: Dict[Tuple[str, str, str], str] = {}
SUBTOPIC_KEY_BY_ID: Dict[str, Tuple[str, str, str]] = {}


def load_words(path: Optional[Path] = None) -> None:
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

    file_path = Path(path) if path else Path(WORDS_FILE)

    print(f"[words_repo] WORDS_FILE = {file_path}")
    print(f"[words_repo] exists = {file_path.exists()}")

    if not file_path.exists():
        print("[words_repo] words.json not found. 0 words loaded.")
        return

    try:
        print(f"[words_repo] size = {file_path.stat().st_size} bytes")
    except Exception:
        pass

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("[words_repo] JSON load error:", e)
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

        key_all = TOPIC_ALL
        key_topic = f"{level}|{topic}"
        key_subtopic = f"{level}|{topic}|{subtopic}"

        WORDS_BY_TOPIC[key_all].append(idx)
        WORDS_BY_TOPIC[key_topic].append(idx)
        WORDS_BY_TOPIC[key_subtopic].append(idx)

        LEVEL_COUNTS[level] += 1
        TOPIC_COUNTS[(level, topic)] += 1
        SUBTOPIC_COUNTS[(level, topic, subtopic)] += 1

    # Формат 1: список блоков
    # [
    #   {"topic":"...", "level":"A1", "subtopic":"...", "words":[{de,tr,ru}, ...]},
    #   ...
    # ]
    if isinstance(data, list):
        for block in data:
            if not isinstance(block, dict):
                continue
            level_raw = block.get("level") or ""
            topic_raw = block.get("topic") or ""
            subtopic_raw = block.get("subtopic") or ""
            words = block.get("words", [])
            if isinstance(words, list):
                for raw in words:
                    if isinstance(raw, dict):
                        add_word(raw, level_raw, topic_raw, subtopic_raw)

    # Формат 2: {"topics":[...]}
    elif isinstance(data, dict) and "topics" in data and isinstance(data["topics"], list):
        for block in data["topics"]:
            if not isinstance(block, dict):
                continue
            level_raw = block.get("level") or ""
            topic_raw = block.get("topic") or ""
            subtopic_raw = block.get("subtopic") or ""
            for raw in block.get("words", []):
                if isinstance(raw, dict):
                    add_word(raw, level_raw, topic_raw, subtopic_raw)
    else:
        print("[words_repo] Unknown words.json format.")
        return

    for i, key in enumerate(sorted(TOPIC_COUNTS.keys())):
        tid = f"t{i}"
        TOPIC_ID_BY_KEY[key] = tid
        TOPIC_KEY_BY_ID[tid] = key

    for i, key in enumerate(sorted(SUBTOPIC_COUNTS.keys())):
        sid = f"s{i}"
        SUBTOPIC_ID_BY_KEY[key] = sid
        SUBTOPIC_KEY_BY_ID[sid] = key

    print(f"[words_repo] Loaded words: {len(WORDS)}")
    print(f"[words_repo] Topics: {len(TOPIC_COUNTS)} | Subtopics: {len(SUBTOPIC_COUNTS)}")


def get_levels() -> List[str]:
    return sorted(LEVEL_COUNTS.keys())


def get_topics_for_level(level: str) -> List[str]:
    topics = [
        topic
        for (lvl, topic), count in TOPIC_COUNTS.items()
        if lvl == level and count > 0
    ]
    return sorted(set(topics))


def get_subtopics_for_level_topic(level: str, topic: str) -> List[str]:
    subs = [
        subtopic
        for (lvl, top, subtopic), count in SUBTOPIC_COUNTS.items()
        if lvl == level and top == topic and count > 0
    ]
    return sorted(set(subs))


def pretty_topic_name(topic_key: str) -> str:
    if not topic_key or topic_key == TOPIC_ALL:
        return "Все слова"
    parts = topic_key.split("|")
    if len(parts) == 3:
        level, topic, subtopic = parts
        return f"Уровень {level}: {topic} -> {subtopic}"
    if len(parts) == 2:
        level, topic = parts
        return f"Уровень {level}: {topic}"
    return topic_key


def get_user_words(topic_key: str) -> List[int]:
    if not topic_key or topic_key == TOPIC_ALL:
        return WORDS_BY_TOPIC.get(TOPIC_ALL, [])
    return WORDS_BY_TOPIC.get(topic_key, [])


def new_shuffled_cycle(topic_key: str) -> List[int]:
    ids = get_user_words(topic_key).copy()
    random.shuffle(ids)
    return ids
