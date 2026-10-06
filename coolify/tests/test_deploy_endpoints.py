"""Regression tests for the deployment commands.

`deploy` and `deployments` both returned HTTP 404 against a real Coolify (4.0.0-beta.469): they
called `POST /applications/{uuid}/deploy` and `GET /applications/{uuid}/deployments`, neither of
which exists. The endpoints that do:

    POST /deploy?uuid=<app_uuid>&force=<bool>  queue a deployment (GET on older Coolify,
                                               used only when POST answers 405)
    GET /deployments                            deployments in flight (no history)
    GET /deployments/<deployment_uuid>          one deployment, with `status`

These tests pin the URLs, because the failure mode is a 404 at the moment you most want the tool to
work — mid-deploy — and nothing else in the suite touches the network.
"""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "coolify_cli.py"
spec = importlib.util.spec_from_file_location("coolify_cli", MODULE)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


@pytest.fixture
def calls(monkeypatch):
    """Record (method, path) and return canned bodies, so nothing reaches the network."""
    recorded = []

    def fake_api(method, path, data=None, **kwargs):
        recorded.append((method, path))
        if path.startswith("/deploy?"):
            return {
                "deployments": [
                    {
                        "message": "queued.",
                        "resource_uuid": "app-uuid",
                        "deployment_uuid": "dep-uuid",
                    }
                ]
            }
        if path == "/deployments":
            return [
                {
                    "deployment_uuid": "dep-uuid",
                    "application_id": 42,
                    "application_name": "mine",
                    "status": "in_progress",
                    "commit": "abcdef1234",
                },
                {
                    "deployment_uuid": "other",
                    "application_id": 99,
                    "application_name": "theirs",
                    "status": "in_progress",
                },
            ]
        if path.startswith("/deployments/"):
            return {"deployment_uuid": path.rsplit("/", 1)[1], "status": "finished"}
        if path.startswith("/applications/"):
            return {"id": 42, "uuid": "app-uuid"}
        raise AssertionError(f"unexpected call: {method} {path}")

    monkeypatch.setattr(cc, "api", fake_api)
    return recorded


def test_deploy_posts_to_the_query_string_endpoint(calls, capsys):
    """Newer Coolify rejects GET /deploy with 405; it used to POST /applications/{uuid}/deploy (404)."""
    cc.cmd_deploy("app-uuid")

    assert calls == [("POST", "/deploy?uuid=app-uuid&force=false")]
    assert "/applications/app-uuid/deploy" not in str(calls)


def test_deploy_falls_back_to_get_only_on_405(monkeypatch, capsys):
    """Older Coolify (4.0.0-beta.469) only accepts GET; a 405 means nothing was queued."""
    recorded = []

    def fake_api(method, path, data=None, passthrough=()):
        recorded.append((method, path, tuple(passthrough)))
        if method == "POST":
            raise cc.ApiStatus(405)
        return {"deployments": [{"deployment_uuid": "dep-uuid", "resource_uuid": "app-uuid"}]}

    monkeypatch.setattr(cc, "api", fake_api)
    cc.cmd_deploy("app-uuid")

    assert recorded == [
        ("POST", "/deploy?uuid=app-uuid&force=false", (405,)),
        ("GET", "/deploy?uuid=app-uuid&force=false", ()),
    ]
    assert "deployment_uuid=dep-uuid" in capsys.readouterr().out


def test_api_passthrough_raises_only_for_listed_status(monkeypatch):
    """Other HTTP errors still exit, so a 401/404 never turns into a silent GET retry."""
    import io
    from urllib.error import HTTPError

    def boom(req, timeout):
        raise HTTPError(req.full_url, 404, "nope", {}, io.BytesIO(b'{"message":"nope"}'))

    monkeypatch.setattr(cc, "urlopen", boom)
    monkeypatch.setattr(cc, "get_config", lambda: ("https://c.example", "t"))
    with pytest.raises(SystemExit):
        cc.api("POST", "/deploy?uuid=x", passthrough=(405,))


def test_deploy_force_is_sent_explicitly(calls):
    """`force` is a value, not a flag whose absence means false — send it either way."""
    cc.cmd_deploy("app-uuid", force=True)

    assert calls == [("POST", "/deploy?uuid=app-uuid&force=true")]


def test_deploy_surfaces_the_deployment_uuid(calls, capsys):
    """Without it there is nothing to poll, which is why it is printed and not just dumped."""
    cc.cmd_deploy("app-uuid")

    assert "deployment_uuid=dep-uuid" in capsys.readouterr().out


def test_deployments_filters_to_one_application(calls, capsys):
    """/deployments keys on the numeric application_id, so the app uuid must be resolved first."""
    cc.cmd_deployments("app-uuid")

    assert ("GET", "/applications/app-uuid") in calls
    assert ("GET", "/deployments") in calls
    out = capsys.readouterr().out
    assert "dep-uuid" in out
    assert "other" not in out, "a different application's deployment leaked into the output"


def test_deployments_without_a_uuid_lists_everything(calls, capsys):
    cc.cmd_deployments()

    assert calls == [("GET", "/deployments")]
    out = capsys.readouterr().out
    assert "dep-uuid" in out and "other" in out


def test_deployments_says_so_when_nothing_is_in_flight(monkeypatch, capsys):
    """An empty list must not read as "this app has never deployed" — there is no history API."""
    monkeypatch.setattr(cc, "api", lambda m, p, data=None: [] if p == "/deployments" else {"id": 1})

    cc.cmd_deployments()

    out = capsys.readouterr().out
    assert "No deployment in progress" in out
    assert "does not return history" in out


def test_deployment_reads_a_single_deployment(calls, capsys):
    cc.cmd_deployment("dep-uuid")

    assert calls == [("GET", "/deployments/dep-uuid")]
    assert "finished" in capsys.readouterr().out
