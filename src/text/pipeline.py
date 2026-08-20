"""Text processing pipeline combining OpenCC and Custom Dictionary."""
from __future__ import annotations

import logging
from pathlib import Path
from ..settings.dictionary_loader import DEFAULT_DICTIONARY_PATH, load_dictionary
from .dictionary import DictionaryCorrector
from .traditional_chinese import TraditionalChineseConverter

logger = logging.getLogger(__name__)


class TextPipeline:
    """End-to-end text processing pipeline:

    ASR Output -> OpenCC (Taiwan Traditional) -> Custom Dictionary -> Final Text
    """

    def __init__(self, dict_path: Path | str = DEFAULT_DICTIONARY_PATH):
        self._converter = TraditionalChineseConverter()
        self._dict_path = Path(dict_path)
        self._corrector = DictionaryCorrector()
        self.reload_dictionary(self._dict_path)

    def reload_dictionary(self, dict_path: Path | str | None = None) -> None:
        """Reload custom dictionary from disk."""
        if dict_path is not None:
            self._dict_path = Path(dict_path)

        dict_data = load_dictionary(self._dict_path)
        self._corrector.load_entries(dict_data)
        logger.info("TextPipeline reloaded dictionary from %s with %d entries.", self._dict_path, len(dict_data.entries))

    def process(self, text: str) -> str:
        """Process raw ASR text through the conversion pipeline.

        1. Strip whitespace
        2. OpenCC (Simplified -> Taiwan Traditional Chinese phrases)
        3. Custom Dictionary replacement (Exact Variant -> Target)
        """
        if not text:
            return ""

        trimmed = text.strip()
        if not trimmed:
            return ""

        # Step 1: OpenCC fallback conversion
        converted = self._converter.convert(trimmed)

        # Step 2: Custom Dictionary deterministic correction
        final_text = self._corrector.correct(converted)

        logger.debug("TextPipeline: '%s' -> '%s' -> '%s'", text, converted, final_text)
        return final_text
