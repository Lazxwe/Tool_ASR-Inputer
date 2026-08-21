"""Custom dictionary loader and validator."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DICTIONARY_PATH = Path("custom_dictionary.json")


@dataclass
class DictionaryEntry:
    """A single custom dictionary entry (Target ← Variants, with optional Context keywords)."""
    target: str
    variants: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)


@dataclass
class DictionaryData:
    """Parsed custom dictionary content."""
    version: int = 1
    entries: list[DictionaryEntry] = field(default_factory=list)


def load_dictionary(dict_path: Path | str = DEFAULT_DICTIONARY_PATH) -> DictionaryData:
    """Load and validate custom dictionary from a JSON file.

    Returns empty DictionaryData if file is missing or contains invalid format.
    Never raises an unhandled exception to prevent application crash.
    """
    path = Path(dict_path)
    if not path.is_file():
        logger.info("Custom dictionary not found at %s. Using empty dictionary.", path)
        return DictionaryData()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Custom dictionary root is not a JSON object. Using empty dictionary.")
            return DictionaryData()

        version = data.get("version", 1)
        if not isinstance(version, int):
            logger.warning("Invalid dictionary version '%s'. Defaulting to 1.", version)
            version = 1

        raw_entries = data.get("entries", [])
        if not isinstance(raw_entries, list):
            logger.warning("Dictionary 'entries' is not a list. Using empty dictionary.")
            return DictionaryData(version=version, entries=[])

        parsed_entries: list[DictionaryEntry] = []
        for index, item in enumerate(raw_entries):
            if not isinstance(item, dict):
                logger.warning("Entry at index %d is not a dict. Skipping.", index)
                continue

            target = item.get("target")
            if not isinstance(target, str) or not target.strip():
                logger.warning("Entry at index %d has invalid target. Skipping.", index)
                continue

            raw_variants = item.get("variants", [])
            if not isinstance(raw_variants, list):
                logger.warning("Entry '%s' has non-list variants. Skipping variants.", target)
                raw_variants = []

            clean_variants: list[str] = [
                v.strip() for v in raw_variants if isinstance(v, str) and v.strip()
            ]

            raw_context = item.get("context", [])
            if not isinstance(raw_context, list):
                logger.warning("Entry '%s' has non-list context. Defaulting to empty context.", target)
                raw_context = []

            clean_context: list[str] = [
                c.strip() for c in raw_context if isinstance(c, str) and c.strip()
            ]

            parsed_entries.append(
                DictionaryEntry(
                    target=target.strip(),
                    variants=clean_variants,
                    context=clean_context,
                )
            )

        logger.info("Loaded %d dictionary entries from %s (version: %d)", len(parsed_entries), path, version)
        return DictionaryData(version=version, entries=parsed_entries)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON dictionary at %s (line %d, col %d): %s", path, e.lineno, e.colno, e.msg)
        return DictionaryData()
    except Exception as e:
        logger.error("Unexpected error loading dictionary from %s: %s", path, e)
        return DictionaryData()


# Alias for explicit naming
load_custom_dictionary = load_dictionary
