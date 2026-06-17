"""Locks the agent-facing contract: tool descriptions, annotations, and enums.

These are not behavior tests; they guard the text and schema the calling agent
relies on, so an accidental edit that strips guidance or an enum fails loudly.
"""

from fastmcp import Client

from sinal_aberto.models import DataSourceStatus, RecentActivityResult, TerritorialContext
from sinal_aberto.server import mcp


async def _tools():
    async with Client(mcp) as client:
        return {tool.name: tool for tool in await client.list_tools()}


# -- annotations -------------------------------------------------------


async def test_tools_are_marked_read_only_and_open_world() -> None:
    tools = await _tools()
    for name in ("get_recent_activity", "list_data_sources"):
        ann = tools[name].annotations
        assert ann is not None and ann.readOnlyHint is True
        assert ann.openWorldHint is True


# -- description carries the operative guidance ------------------------


async def test_recent_activity_description_guides_the_agent() -> None:
    desc = (await _tools())["get_recent_activity"].description.lower()
    # the agent must learn how to react to ambiguity and to avoid codes
    assert "match_quality" in desc
    assert "numeric codes" in desc
    # evidence and confidence are explicitly distinguished
    assert "evidence_level" in desc and "confidence_level" in desc


# -- enums reach the schema -------------------------------------------


def test_result_enums_are_published() -> None:
    schema = RecentActivityResult.model_json_schema()
    props = schema["properties"]
    assert set(props["evidence_level"]["enum"]) == {
        "no evidence",
        "no recent evidence",
        "low evidence",
        "moderate evidence",
        "high evidence",
    }
    assert set(props["confidence_level"]["enum"]) == {"low", "medium", "high"}


def test_match_quality_enum_is_published() -> None:
    schema = TerritorialContext.model_json_schema()
    assert set(schema["properties"]["match_quality"]["enum"]) == {
        "exact",
        "approximate",
        "ambiguous",
    }


def test_source_status_enum_is_published() -> None:
    schema = DataSourceStatus.model_json_schema()
    assert set(schema["properties"]["status"]["enum"]) == {
        "operational",
        "unavailable",
        "integrated",
        "validated, not integrated",
    }
