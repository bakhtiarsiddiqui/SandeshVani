"""LangGraph shared state type for the AI Campaign Assistant pipeline."""

from __future__ import annotations

import uuid
from typing import TypedDict

from ai.schemas import CampaignBrief, GeneratedDraft


class PipelineState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes.

    Fields are set progressively as nodes execute. All fields are optional
    at the TypedDict level because nodes receive partial state.
    """

    # Set by the entry point
    request_id: uuid.UUID
    brief: CampaignBrief

    # Set by the generate node
    raw_text: str
    provider_name: str
    provider_model: str

    # Set by the validate node
    draft: GeneratedDraft
    validation_warnings: list[str]

    # Set by the persist node
    persisted: bool
    error: str | None
