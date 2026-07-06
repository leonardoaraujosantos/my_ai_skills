"""Regression guard for mcp-client attribute-name bugs.

These bugs can't be exercised without a live MCP server, so this locks in the
source-level fix instead:
  * resource templates read from `resourceTemplates` (the real SDK field), not
    the always-absent `resource_templates`.
  * serverInfo is captured from the initialize() result and attached to the
    session (the session itself never had a `server_info` attribute).

If the installed mcp SDK is present, also assert the field names are real.
"""

from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "scripts" / "mcp_client.py").read_text()


def test_uses_correct_resource_templates_field():
    assert "resourceTemplates" in SRC
    assert "r.resource_templates" not in SRC


def test_serverinfo_is_captured_from_initialize():
    assert "session.server_info = getattr(init_result" in SRC
    assert 'getattr(init_result, "serverInfo"' in SRC


def test_field_names_match_installed_sdk_if_available():
    try:
        from mcp.types import ListResourceTemplatesResult, InitializeResult
    except Exception:
        return  # SDK not installed in this environment — source guard still ran
    assert "resourceTemplates" in ListResourceTemplatesResult.model_fields
    assert "serverInfo" in InitializeResult.model_fields
