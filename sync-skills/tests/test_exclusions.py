"""Regression tests for sync-skills secret/scope exclusion.

Covers the security fix: a *populated* pentest security-scope.yaml (real target
hostnames) must never be copied into the public repo, while the placeholder
template still syncs. Also verifies the existing secret-file exclusions.
"""

import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "sync_skills.py"
spec = importlib.util.spec_from_file_location("sync_skills", MODULE)
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

TEMPLATE = 'authorized_by: "REPLACE_ME"\nauthorization_date: "YYYY-MM-DD"\n'
POPULATED = 'authorized_by: "Blue Team"\nauthorization_date: "2026-01-01"\n' \
            'assets:\n  - name: "app.realcorp.com"\n'


def test_secret_files_are_ignored(tmp_path):
    names = ["SKILL.md", "tokens.json", "profiles.json", ".env", ".credentials.json"]
    for n in names:
        (tmp_path / n).write_text("x")
    ignored = ss._ignore_sensitive(str(tmp_path), names)
    assert "tokens.json" in ignored
    assert "profiles.json" in ignored
    assert ".env" in ignored
    assert ".credentials.json" in ignored
    assert "SKILL.md" not in ignored


def test_populated_scope_is_excluded(tmp_path):
    (tmp_path / "security-scope.yaml").write_text(POPULATED)
    ignored = ss._ignore_sensitive(str(tmp_path), ["security-scope.yaml"])
    assert "security-scope.yaml" in ignored


def test_template_scope_is_synced(tmp_path):
    (tmp_path / "security-scope.yaml").write_text(TEMPLATE)
    ignored = ss._ignore_sensitive(str(tmp_path), ["security-scope.yaml"])
    assert "security-scope.yaml" not in ignored


def test_is_populated_scope_helper(tmp_path):
    tpl = tmp_path / "tpl.yaml"
    tpl.write_text(TEMPLATE)
    real = tmp_path / "real.yaml"
    real.write_text(POPULATED)
    assert ss._is_populated_scope(real) is True
    assert ss._is_populated_scope(tpl) is False


def test_sync_skills_no_longer_self_excludes():
    # Removing the self-exclusion fixes the sync-skills-drifts-forever bug.
    assert "sync-skills" not in ss.EXCLUDE_SKILLS
