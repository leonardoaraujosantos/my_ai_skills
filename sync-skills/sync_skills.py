#!/usr/bin/env python3
"""
Sync Claude Code Skills to GitHub Repository

Syncs skills from ~/.claude/skills/ to the my_ai_skills repository.

Usage:
    python sync_skills.py [options]

Options:
    --skill <name>      Sync only a specific skill
    --message <msg>     Custom commit message
    --dry-run           Show what would be synced without making changes
    --list              List all available skills
    --help              Show this help message

Examples:
    python sync_skills.py                           # Sync all skills
    python sync_skills.py --skill youtube-playlist  # Sync specific skill
    python sync_skills.py --message "Fix bug in CC extraction"
    python sync_skills.py --dry-run                 # Preview changes
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
SKILLS_DIR = Path.home() / ".claude" / "skills"
REPO_URL = "https://github.com/leonardoaraujosantos/my_ai_skills.git"
REPO_LOCAL = Path("/tmp/my_ai_skills")

# Skills to sync (exclude this skill itself to avoid recursion)
EXCLUDE_SKILLS = {"sync-skills"}


def run_cmd(cmd, cwd=None, check=True):
    """Run a shell command and return output."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip()


def list_skills():
    """List all available skills."""
    if not SKILLS_DIR.exists():
        print("No skills directory found.")
        return []

    skills = []
    for item in SKILLS_DIR.iterdir():
        if item.is_dir() and item.name not in EXCLUDE_SKILLS:
            skill_file = item / "SKILL.md"
            if skill_file.exists():
                skills.append(item.name)
    return sorted(skills)


def clone_or_pull_repo():
    """Clone the repo or pull latest changes."""
    if REPO_LOCAL.exists():
        print("Pulling latest changes...")
        result = run_cmd("git pull origin main", cwd=REPO_LOCAL, check=False)
        if result is None:
            print("Warning: Could not pull, continuing with local copy...")
    else:
        print("Cloning repository...")
        run_cmd(f"git clone {REPO_URL} {REPO_LOCAL}")

    return REPO_LOCAL.exists()


def sync_skill(skill_name, dry_run=False):
    """Sync a single skill to the repo."""
    source = SKILLS_DIR / skill_name
    dest = REPO_LOCAL / skill_name

    if not source.exists():
        print(f"Skill not found: {skill_name}")
        return False

    if dry_run:
        print(f"Would sync: {skill_name}")
        for item in source.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(source)
                print(f"  - {rel_path}")
        return True

    # Remove existing destination
    if dest.exists():
        shutil.rmtree(dest)

    # Copy skill
    shutil.copytree(source, dest)
    print(f"Synced: {skill_name}")
    return True


def get_changes(repo_path):
    """Get list of changed files."""
    result = run_cmd("git status --porcelain", cwd=repo_path, check=False)
    if result:
        return [line.strip() for line in result.split("\n") if line.strip()]
    return []


def commit_and_push(message, repo_path):
    """Commit and push changes."""
    # Stage all changes
    run_cmd("git add .", cwd=repo_path)

    # Check if there are changes to commit
    changes = get_changes(repo_path)
    if not changes:
        print("No changes to commit.")
        return False

    # Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_message = f"{message}\n\nSynced at: {timestamp}"

    # Use a file for commit message to handle special characters
    msg_file = repo_path / ".commit_msg"
    msg_file.write_text(full_message)

    result = run_cmd(f'git commit -F .commit_msg', cwd=repo_path, check=False)
    msg_file.unlink()  # Clean up

    if result is None:
        print("Commit failed.")
        return False

    print(f"Committed: {message}")

    # Push
    result = run_cmd("git push origin main", cwd=repo_path, check=False)
    if result is None:
        print("Push failed. You may need to push manually.")
        return False

    print("Pushed to GitHub.")
    return True


def generate_commit_message(synced_skills):
    """Generate a commit message based on synced skills."""
    if len(synced_skills) == 1:
        return f"Update {synced_skills[0]} skill"
    elif len(synced_skills) <= 3:
        return f"Update skills: {', '.join(synced_skills)}"
    else:
        return f"Update {len(synced_skills)} skills"


def print_help():
    """Print help message."""
    print(__doc__)


def main():
    args = sys.argv[1:]

    # Parse arguments
    skill_name = None
    message = None
    dry_run = False
    show_list = False

    i = 0
    while i < len(args):
        if args[i] == '--help':
            print_help()
            return
        elif args[i] == '--skill' and i + 1 < len(args):
            skill_name = args[i + 1]
            i += 2
        elif args[i] == '--message' and i + 1 < len(args):
            message = args[i + 1]
            i += 2
        elif args[i] == '--dry-run':
            dry_run = True
            i += 1
        elif args[i] == '--list':
            show_list = True
            i += 1
        else:
            i += 1

    # List skills
    if show_list:
        skills = list_skills()
        print("Available skills:")
        for s in skills:
            print(f"  - {s}")
        return

    # Clone/pull repo
    if not dry_run:
        if not clone_or_pull_repo():
            print("Error: Could not access repository.")
            sys.exit(1)
    else:
        print("=== DRY RUN ===\n")

    # Determine which skills to sync
    if skill_name:
        skills_to_sync = [skill_name]
    else:
        skills_to_sync = list_skills()

    if not skills_to_sync:
        print("No skills to sync.")
        return

    # Sync skills
    synced = []
    for skill in skills_to_sync:
        if sync_skill(skill, dry_run):
            synced.append(skill)

    if dry_run:
        print(f"\n=== Would sync {len(synced)} skill(s) ===")
        return

    if not synced:
        print("No skills were synced.")
        return

    # Commit and push
    if not message:
        message = generate_commit_message(synced)

    commit_and_push(message, REPO_LOCAL)

    print(f"\nSynced {len(synced)} skill(s) to {REPO_URL}")


if __name__ == "__main__":
    main()
