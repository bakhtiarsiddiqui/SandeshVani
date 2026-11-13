"""Strict allowlisted segment filter AST validation and SQL expression compilation."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, func, or_

from app.models.audience_member import AudienceMember
from app.schemas.audience import INDIA_STATE_UT_CODES

MAX_DEPTH = 5
MAX_PREDICATES = 20
MAX_GROUP_CHILDREN = 10

_STRING_FIELDS = {
    "status": AudienceMember.status,
    "district": AudienceMember.district,
    "state_code": AudienceMember.state_code,
    "city": AudienceMember.city,
    "preferred_language": AudienceMember.preferred_language,
}
_BOOLEAN_FIELDS = {
    "has_email": AudienceMember.email,
    "has_phone": AudienceMember.phone,
}


class SegmentFilterError(ValueError):
    """Raised when a user-supplied segment AST is outside the allowlist."""


def _validate_leaf(field: str, operator: str, value: Any) -> None:
    if field in _STRING_FIELDS:
        if operator == "eq":
            values = [value]
        elif operator == "in":
            if not isinstance(value, list) or not 1 <= len(value) <= 100:
                raise SegmentFilterError(
                    "in requires a list of 1 to 100 values"
                )
            values = value
        else:
            raise SegmentFilterError(
                "String fields support only eq and in"
            )
        if any(not isinstance(item, str) or not item.strip() for item in values):
            raise SegmentFilterError(
                "String filter values must be non-blank strings"
            )
        if field == "status" and any(
            item not in {"active", "inactive"} for item in values
        ):
            raise SegmentFilterError("Unsupported audience status value")
        if field == "preferred_language" and any(
            item not in {"en", "hi"} for item in values
        ):
            raise SegmentFilterError("Unsupported preferred language")
        if field == "state_code" and any(
            item.strip().upper() not in INDIA_STATE_UT_CODES for item in values
        ):
            raise SegmentFilterError("Unsupported State / UT code")
        if any(len(item) > 150 for item in values):
            raise SegmentFilterError("Filter value exceeds the field length limit")
        return
    if field in _BOOLEAN_FIELDS:
        if operator != "eq" or not isinstance(value, bool):
            raise SegmentFilterError("Boolean fields support eq with a boolean value")
        return
    raise SegmentFilterError("Filter field is not allowlisted")


def validate_segment_filter(ast: dict[str, Any]) -> dict[str, Any]:
    """Validate AST grammar and bounded complexity, returning a safe copy."""
    if not isinstance(ast, dict):
        raise SegmentFilterError("Segment filter must be an object")
    predicate_count = 0

    def walk(node: Any, depth: int) -> dict[str, Any]:
        nonlocal predicate_count
        if depth > MAX_DEPTH or not isinstance(node, dict):
            raise SegmentFilterError(
                "Segment filter nesting is invalid or too deep"
            )
        if set(node) == {"op", "children"}:
            operation = node["op"]
            children = node["children"]
            if operation not in {"and", "or"}:
                raise SegmentFilterError("Group operation must be and or or")
            if (
                not isinstance(children, list)
                or not 2 <= len(children) <= MAX_GROUP_CHILDREN
            ):
                raise SegmentFilterError("Groups require 2 to 10 child predicates")
            return {
                "op": operation,
                "children": [walk(child, depth + 1) for child in children],
            }
        if set(node) != {"field", "operator", "value"}:
            raise SegmentFilterError(
                "Predicate must contain only field, operator and value"
            )
        field = node["field"]
        operator = node["operator"]
        if not isinstance(field, str) or not isinstance(operator, str):
            raise SegmentFilterError("Predicate field and operator must be strings")
        _validate_leaf(field, operator, node["value"])
        predicate_count += 1
        if predicate_count > MAX_PREDICATES:
            raise SegmentFilterError("Segment filter exceeds the predicate limit")
        value = node["value"]
        if field == "state_code":
            value = (
                [item.strip().upper() for item in value]
                if isinstance(value, list)
                else value.strip().upper()
            )
        if field in {"district", "city"}:
            value = (
                [item.strip() for item in value]
                if isinstance(value, list)
                else value.strip()
            )
        return {"field": field, "operator": operator, "value": value}

    return walk(ast, 1)


def compile_segment_filter(ast: dict[str, Any]):
    """Translate a previously validated AST to SQLAlchemy expressions."""
    safe_ast = validate_segment_filter(ast)

    def compile_node(node: dict[str, Any]):
        if "op" in node:
            clauses = [compile_node(child) for child in node["children"]]
            return and_(*clauses) if node["op"] == "and" else or_(*clauses)
        field = node["field"]
        operator = node["operator"]
        value = node["value"]
        if field in _BOOLEAN_FIELDS:
            column = _BOOLEAN_FIELDS[field]
            return column.is_not(None) if value else column.is_(None)
        column = _STRING_FIELDS[field]
        if field in {"city", "district"}:
            expression = func.lower(column)
            if operator == "eq":
                return expression == value.lower()
            return expression.in_([item.lower() for item in value])
        if operator == "eq":
            return column == value
        return column.in_(value)

    return compile_node(safe_ast)
