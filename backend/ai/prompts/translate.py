"""Translation prompt builders.

Returns (system, user) string pairs ready to pass to any LLMProvider.
"""

from __future__ import annotations

_TRANSLATE_SYSTEM = """\
You are a professional translator. Translate the following text accurately and \
naturally into the target language. Output ONLY the translated text — no \
explanations, no alternatives, no quotes around the result.\
"""


def build_translation_prompt(
    text: str,
    source_lang: str,
    target_lang: str,
) -> tuple[str, str]:
    """Build the system and user prompt strings for a translation request.

    Returns:
        (system_prompt, user_prompt)
    """
    user = (
        f"Source language: {source_lang}\n"
        f"Target language: {target_lang}\n"
        f"\n"
        f"Text to translate:\n{text}"
    )
    return _TRANSLATE_SYSTEM, user
