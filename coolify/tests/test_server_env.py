"""Regression tests for coolify server env-var derivation.

Locks in the portability change: instead of a hardcoded personal server list,
any `--server <name>` maps to COOLIFY_<NAME>_URL / COOLIFY_<NAME>_TOKEN, and the
default server reads the bare COOLIFY_URL / COOLIFY_TOKEN.
"""

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "coolify_cli.py"
spec = importlib.util.spec_from_file_location("coolify_cli", MODULE)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def test_default_server_uses_bare_env():
    assert cc._env_names("sandbox") == ("COOLIFY_URL", "COOLIFY_TOKEN")


@pytest.mark.parametrize("name,expected", [
    ("prd", ("COOLIFY_PRD_URL", "COOLIFY_PRD_TOKEN")),
    ("staging", ("COOLIFY_STAGING_URL", "COOLIFY_STAGING_TOKEN")),
    ("my-stg", ("COOLIFY_MY_STG_URL", "COOLIFY_MY_STG_TOKEN")),
    ("prod.eu", ("COOLIFY_PROD_EU_URL", "COOLIFY_PROD_EU_TOKEN")),
])
def test_named_server_derives_prefixed_env(name, expected):
    assert cc._env_names(name) == expected


def test_no_hardcoded_server_list():
    # The old personal SERVERS dict (with a cyberdyne entry) must be gone.
    assert not hasattr(cc, "SERVERS")


def test_get_config_errors_when_env_missing(monkeypatch, capsys):
    monkeypatch.setattr(cc, "_active_server", "prd")
    monkeypatch.delenv("COOLIFY_PRD_URL", raising=False)
    monkeypatch.delenv("COOLIFY_PRD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        cc.get_config()
    assert "COOLIFY_PRD_URL" in capsys.readouterr().err
