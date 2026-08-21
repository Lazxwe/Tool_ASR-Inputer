"""Custom dictionary deterministic replacement engine with Level 2 Context-Aware matching."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence
from ..settings.dictionary_loader import DictionaryData, DictionaryEntry

logger = logging.getLogger(__name__)

CLAUSE_DELIMITERS = frozenset("，。！？；\n\r,!?;:\t")
DEFAULT_WINDOW_SIZE = 25


@dataclass
class _CompiledRule:
    """Internal representation of a compiled dictionary replacement rule."""
    target: str
    variant: str
    context: list[str]

    @property
    def is_exact(self) -> bool:
        """True if the rule has no context constraints (unconditional replacement)."""
        return len(self.context) == 0


@dataclass
class _MatchCandidate:
    """A matched candidate interval and its applied rule."""
    start: int
    end: int
    rule: _CompiledRule


class DictionaryCorrector:
    """Performs deterministic string replacement with Level 2 Context-Aware support.

    Rule Structure: Target ← Variants (with optional Context keywords)
    
    Matching Algorithm:
    1. Exact Rules (no context specified): Replaced unconditionally across the text.
    2. Contextual Rules (context list specified): Replaced only when at least one context
       keyword appears within the sliding window (clause-bounded by default) around the variant.
    3. Conflict Resolution: Longest variants take precedence, and contextual matches are prioritized
       over generic matches of equal length.
    """

    def __init__(
        self,
        dictionary_data: DictionaryData | Sequence[DictionaryEntry] | None = None,
        window_size: int = DEFAULT_WINDOW_SIZE,
        clause_aware: bool = True,
    ):
        self.window_size = window_size
        self.clause_aware = clause_aware
        self._rules: list[_CompiledRule] = []
        if dictionary_data is not None:
            self.load_entries(dictionary_data)

    @property
    def rules(self) -> list[_CompiledRule]:
        """Return the compiled replacement rules."""
        return self._rules

    @property
    def _replacement_map(self) -> dict[str, str]:
        """Backward compatibility dictionary map mapping variant -> target."""
        return {r.variant: r.target for r in self._rules}

    def load_entries(self, dictionary_data: DictionaryData | Sequence[DictionaryEntry]) -> None:
        """Load entries and compile replacement rules."""
        entries: Sequence[DictionaryEntry]
        if isinstance(dictionary_data, DictionaryData):
            entries = dictionary_data.entries
        else:
            entries = dictionary_data

        self._rules.clear()
        for entry in entries:
            target = entry.target
            for variant in entry.variants:
                if variant and variant != target:
                    self._rules.append(
                        _CompiledRule(
                            target=target,
                            variant=variant,
                            context=entry.context,
                        )
                    )

        # Sort rules primarily by variant length descending (longest match first)
        self._rules.sort(key=lambda r: len(r.variant), reverse=True)
        exact_count = sum(1 for r in self._rules if r.is_exact)
        context_count = len(self._rules) - exact_count
        logger.debug(
            "DictionaryCorrector loaded %d rules (Exact: %d, Context-Aware: %d).",
            len(self._rules),
            exact_count,
            context_count,
        )

    def _extract_context_window(self, text: str, start: int, end: int) -> str:
        """Extract the local context window around [start, end], bounded by clauses if enabled."""
        if not self.clause_aware:
            left = max(0, start - self.window_size)
            right = min(len(text), end + self.window_size)
            return text[left:right]

        left_limit = max(0, start - self.window_size)
        right_limit = min(len(text), end + self.window_size)

        left_bound = left_limit
        for i in range(start - 1, left_limit - 1, -1):
            if text[i] in CLAUSE_DELIMITERS:
                left_bound = i + 1
                break

        right_bound = right_limit
        for i in range(end, right_limit):
            if text[i] in CLAUSE_DELIMITERS:
                right_bound = i
                break

        return text[left_bound:right_bound]

    def _is_context_satisfied(self, text: str, start: int, end: int, rule: _CompiledRule) -> bool:
        """Check if any required context keyword is present within the window."""
        if rule.is_exact:
            return True

        window_text = self._extract_context_window(text, start, end)
        return any(kw in window_text for kw in rule.context)

    def correct(self, text: str) -> str:
        """Replace all registered variants with their target strings according to context rules.

        Returns unchanged text if no matches or text is empty.
        """
        if not text or not self._rules:
            return text

        try:
            candidates: list[_MatchCandidate] = []

            # 1. Discover all matching occurrences for each rule
            for rule in self._rules:
                var_len = len(rule.variant)
                find_start = 0
                while True:
                    idx = text.find(rule.variant, find_start)
                    if idx == -1:
                        break
                    match_end = idx + var_len
                    if self._is_context_satisfied(text, idx, match_end, rule):
                        candidates.append(_MatchCandidate(start=idx, end=match_end, rule=rule))
                    find_start = idx + 1

            if not candidates:
                return text

            # 2. Sort candidates by:
            # - Length descending (longest match)
            # - Rule specificity (contextual rule comes before exact rule)
            # - Position ascending
            candidates.sort(
                key=lambda c: (
                    -(c.end - c.start),
                    0 if not c.rule.is_exact else 1,
                    c.start,
                )
            )

            # 3. Select non-overlapping intervals (Greedy interval scheduling)
            selected: list[_MatchCandidate] = []
            for cand in candidates:
                # Check overlap with any accepted candidate
                overlaps = any(
                    not (cand.end <= s.start or cand.start >= s.end)
                    for s in selected
                )
                if not overlaps:
                    selected.append(cand)

            if not selected:
                return text

            # 4. Sort selected candidates by start index ascending for reconstruction
            selected.sort(key=lambda c: c.start)

            # 5. Reconstruct final string
            pieces: list[str] = []
            cursor = 0
            for cand in selected:
                pieces.append(text[cursor:cand.start])
                pieces.append(cand.rule.target)
                cursor = cand.end
            pieces.append(text[cursor:])

            return "".join(pieces)

        except Exception as e:
            logger.error("Error during dictionary replacement on text '%s': %s", text, e)
            return text
