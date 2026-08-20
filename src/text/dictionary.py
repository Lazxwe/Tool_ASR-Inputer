"""Custom dictionary deterministic replacement engine."""
from __future__ import annotations

import logging
import re
from typing import Sequence
from ..settings.dictionary_loader import DictionaryData, DictionaryEntry

logger = logging.getLogger(__name__)


class DictionaryCorrector:
    """Performs exact variant string replacement based on custom dictionary rules.

    Pattern: Target ← Variants
    Longer variants are matched and replaced first to prevent prefix shadowing.
    """

    def __init__(self, dictionary_data: DictionaryData | Sequence[DictionaryEntry] | None = None):
        self._replacement_map: dict[str, str] = {}
        self._sorted_patterns: list[tuple[re.Pattern[str], str]] = []
        if dictionary_data is not None:
            self.load_entries(dictionary_data)

    def load_entries(self, dictionary_data: DictionaryData | Sequence[DictionaryEntry]) -> None:
        """Load entries and compile optimized replacement regex rules."""
        entries: Sequence[DictionaryEntry]
        if isinstance(dictionary_data, DictionaryData):
            entries = dictionary_data.entries
        else:
            entries = dictionary_data

        self._replacement_map.clear()
        for entry in entries:
            target = entry.target
            for variant in entry.variants:
                if variant and variant != target:
                    self._replacement_map[variant] = target

        # Sort variants by length descending so longer words take precedence over substrings
        sorted_variants = sorted(self._replacement_map.keys(), key=len, reverse=True)
        if sorted_variants:
            # Compile a single regex matching any variant escaped
            pattern_str = "|".join(re.escape(v) for v in sorted_variants)
            self._compiled_regex = re.compile(pattern_str)
        else:
            self._compiled_regex = None

        logger.debug("DictionaryCorrector loaded %d variant replacement rules.", len(self._replacement_map))

    def correct(self, text: str) -> str:
        """Replace all registered variants with their target strings.

        Returns unchanged text if no matches or text is empty.
        """
        if not text or not self._compiled_regex:
            return text

        def _replace_match(match: re.Match[str]) -> str:
            matched_str = match.group(0)
            return self._replacement_map.get(matched_str, matched_str)

        try:
            return self._compiled_regex.sub(_replace_match, text)
        except Exception as e:
            logger.error("Error during dictionary replacement on text '%s': %s", text, e)
            return text
