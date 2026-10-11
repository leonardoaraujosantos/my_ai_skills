"""Regression tests for scripts/validate_skills.py.

Bug fixed: 26 skills had an unquoted `argument-hint: [cmd] [args...]`, which a
YAML parser reads as a flow sequence followed by junk. The validator flagged
them, so CI on main failed on every push. The frontmatter values are now
quoted; this test keeps the repo in that state and pins the validator's
indicator check so the error cannot silently come back.
"""

import importlib.util
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_skills.py"

spec = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
validate_skills = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_skills)


def test_repo_validates_cleanly():
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = validate_skills.main()
    assert rc == 0, err.getvalue()
    assert "ERROR" not in err.getvalue()


def test_no_skill_has_unquoted_flow_indicator_argument_hint():
    offenders = []
    for skill_md in sorted(ROOT.glob("*/SKILL.md")):
        fm = validate_skills.read_frontmatter(skill_md)
        hint = validate_skills.top_level_keys(fm).get("argument-hint")
        if hint and hint[:1] in validate_skills.YAML_INDICATORS and not validate_skills.is_quoted(hint):
            offenders.append(skill_md.parent.name)
    assert offenders == []


def test_is_quoted_accepts_both_quote_styles():
    assert validate_skills.is_quoted('"[a|b] [args...]"')
    assert validate_skills.is_quoted("'[a|b] [args...]'")
    assert not validate_skills.is_quoted("[a|b] [args...]")
    assert not validate_skills.is_quoted('"unbalanced')


def test_quoted_hint_round_trips_through_a_yaml_parser():
    """The quoted form must be a plain string once parsed (pyyaml optional in CI)."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return
    for skill_md in sorted(ROOT.glob("*/SKILL.md")):
        fm = validate_skills.read_frontmatter(skill_md)
        data = yaml.safe_load(fm)
        assert data["name"] == skill_md.parent.name
        hint = data.get("argument-hint")
        assert hint is None or isinstance(hint, str), f"{skill_md}: argument-hint parsed as {type(hint).__name__}"
