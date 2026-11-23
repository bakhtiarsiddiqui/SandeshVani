"""LangGraph pipeline for AI campaign draft generation.

Graph structure:
  generate → validate → persist → END

The pipeline is stateless across calls: each invocation receives a fresh
PipelineState, runs all nodes, and returns the final state dict.

The AI **never publishes** content. The 'persist' node saves drafts with
status='pending_approval'; a human must explicitly approve before the draft
can enter the campaign workflow.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langgraph.graph import END, StateGraph

from ai.prompts.campaign import build_campaign_system_prompt, build_campaign_user_prompt
from ai.providers.base import LLMProvider
from ai.schemas import GeneratedDraft
from ai.state import PipelineState
from ai.validators import validate_draft

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------


def _make_generate_node(provider: LLMProvider):
    """Factory: returns a generate node bound to the given provider."""

    async def generate(state: PipelineState) -> dict[str, Any]:
        brief = state["brief"]
        system = build_campaign_system_prompt()
        prompt = build_campaign_user_prompt(brief)
        logger.info(
            "Generating draft: provider=%s model=%s channel=%s lang=%s",
            provider.name,
            provider.model,
            brief.channel,
            brief.language,
        )
        raw_text = await provider.generate(prompt=prompt, system=system)
        return {
            "raw_text": raw_text,
            "provider_name": provider.name,
            "provider_model": provider.model,
        }

    return generate


def _validate_node(state: PipelineState) -> dict[str, Any]:
    """Build the GeneratedDraft object and run all validators."""
    brief = state["brief"]
    raw_text = state["raw_text"]

    draft = GeneratedDraft.build(
        language=brief.language,
        channel=brief.channel,
        text=raw_text,
        provider=state.get("provider_name", "unknown"),
        model=state.get("provider_model", "unknown"),
    )

    key_facts_dict = brief.key_facts.model_dump()
    warnings = validate_draft(draft, key_facts_dict, tone=brief.tone)

    if warnings:
        logger.warning(
            "Validation warnings for request %s: %s", state["request_id"], warnings
        )

    return {"draft": draft, "validation_warnings": warnings}


def _make_persist_node(db_writer):
    """Factory: returns a persist node that uses the supplied async db_writer.

    db_writer signature:
        async def write(request_id, brief, draft, warnings) -> None
    """

    async def persist(state: PipelineState) -> dict[str, Any]:
        try:
            await db_writer(
                request_id=state["request_id"],
                brief=state["brief"],
                draft=state["draft"],
                warnings=state.get("validation_warnings", []),
            )
            return {"persisted": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to persist draft: %s", exc)
            return {"persisted": False, "error": str(exc)}

    return persist


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_pipeline(provider: LLMProvider, db_writer) -> StateGraph:
    """Construct and compile the LangGraph pipeline.

    Args:
        provider:  An LLMProvider (real or fake).
        db_writer: Async callable that persists the draft to the database.

    Returns:
        A compiled LangGraph that accepts PipelineState dicts.
    """
    graph = StateGraph(PipelineState)

    graph.add_node("generate", _make_generate_node(provider))
    graph.add_node("validate", _validate_node)
    graph.add_node("persist", _make_persist_node(db_writer))

    graph.set_entry_point("generate")
    graph.add_edge("generate", "validate")
    graph.add_edge("validate", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_pipeline(
    brief,
    provider: LLMProvider,
    db_writer,
    request_id: uuid.UUID | None = None,
) -> PipelineState:
    """Run the full generation pipeline and return the final state.

    Args:
        brief:      CampaignBrief input.
        provider:   LLMProvider to use for generation.
        db_writer:  Async callable to persist the draft.
        request_id: Optional UUID; a new one is generated if not supplied.

    Returns:
        Final PipelineState after all nodes have run.
    """
    request_id = request_id or uuid.uuid4()
    initial_state: PipelineState = {
        "request_id": request_id,
        "brief": brief,
    }
    pipeline = build_pipeline(provider, db_writer)
    final_state: PipelineState = await pipeline.ainvoke(initial_state)
    return final_state
