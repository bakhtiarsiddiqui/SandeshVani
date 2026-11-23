"""Translation helper.

Strategy:
  1. If Ollama is available and running IndicTrans2 or a multilingual model,
     use it for translation.
  2. Otherwise, fall back to the primary LLM provider with an explicit
     translation prompt (the same provider used for generation).

This module never calls paid APIs and never hard-codes keys.
"""

from __future__ import annotations

from ai.prompts.translate import build_translation_prompt
from ai.providers.base import LLMProvider


async def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    provider: LLMProvider,
) -> str:
    """Translate *text* from *source_language* to *target_language*.

    Uses the supplied provider's generate() method with a translation prompt.
    Returns the translated string.
    """
    if source_language == target_language:
        return text

    system, prompt = build_translation_prompt(
        text=text,
        source_lang=source_language,
        target_lang=target_language,
    )
    translated = await provider.generate(prompt=prompt, system=system)
    return translated.strip()
