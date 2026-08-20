"""Traditional Chinese conversion layer using OpenCC."""
from __future__ import annotations

import logging
from opencc import OpenCC

logger = logging.getLogger(__name__)


class TraditionalChineseConverter:
    """Converts Simplified Chinese to Taiwan Traditional Chinese phrases."""

    def __init__(self, config_name: str = "s2twp"):
        """Initialize OpenCC converter with standard Taiwan Traditional config."""
        try:
            self._converter = OpenCC(config_name)
            logger.debug("OpenCC initialized with config '%s'", config_name)
        except Exception as e:
            logger.error("Failed to initialize OpenCC with config '%s': %s", config_name, e)
            self._converter = None

    def convert(self, text: str) -> str:
        """Convert input text to Taiwan Traditional Chinese.

        Returns original text if converter is unavailable or if conversion fails.
        """
        if not text:
            return ""

        if self._converter is None:
            return text

        try:
            return self._converter.convert(text)
        except Exception as e:
            logger.error("Error during OpenCC conversion for text '%s': %s", text, e)
            return text
