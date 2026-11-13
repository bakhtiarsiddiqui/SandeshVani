import pytest

from app.services.segment_filters import (
    SegmentFilterError,
    compile_segment_filter,
    validate_segment_filter,
)


def test_segment_filter_accepts_only_allowlisted_fields_and_operators():
    expression = compile_segment_filter(
        {
            "op": "and",
            "children": [
                {"field": "state_code", "operator": "eq", "value": "IN-UP"},
                {"field": "has_phone", "operator": "eq", "value": True},
                {
                    "op": "or",
                    "children": [
                        {"field": "city", "operator": "eq", "value": "Meerut"},
                        {
                            "field": "preferred_language",
                            "operator": "in",
                            "value": ["en", "hi"],
                        },
                    ],
                },
            ],
        }
    )
    assert expression is not None
    assert "audience_members.state_code" in str(expression)
    assert "audience_members.phone" in str(expression)


@pytest.mark.parametrize(
    "ast",
    [
        {"field": "email", "operator": "eq", "value": "someone@example.test"},
        {"field": "status", "operator": "contains", "value": "active"},
        {"field": "state_code", "operator": "eq", "value": "IN-NOT-A-STATE"},
        {"field": "has_email", "operator": "in", "value": [True, False]},
        {"field": "city", "operator": "in", "value": []},
        {"field": "city", "operator": "eq", "value": ""},
        {"field": "city", "operator": "eq", "value": "x", "sql": "DROP TABLE"},
    ],
)
def test_segment_filter_rejects_unknown_fields_bad_operators_and_values(ast):
    with pytest.raises(SegmentFilterError):
        validate_segment_filter(ast)


def test_segment_filter_rejects_excessive_depth_and_predicate_count():
    nested = {"field": "status", "operator": "eq", "value": "active"}
    for _ in range(6):
        nested = {
            "op": "and",
            "children": [
                nested,
                {"field": "status", "operator": "eq", "value": "active"},
            ],
        }
    with pytest.raises(SegmentFilterError):
        validate_segment_filter(nested)

    leaf = {"field": "status", "operator": "eq", "value": "active"}
    too_many = {
        "op": "and",
        "children": [
            {"op": "and", "children": [leaf, leaf, leaf]}
            for _ in range(7)
        ],
    }
    with pytest.raises(SegmentFilterError):
        validate_segment_filter(too_many)
