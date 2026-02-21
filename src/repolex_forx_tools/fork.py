#!/usr/bin/env python3
"""
fork.py - Fork repos into the repolex-forx organization

Usage:
    python fork.py numpy/numpy                    # Fork a single repo
    python fork.py --seed seeds/python-core.txt  # Fork all repos in a seed file
    python fork.py --pending                      # Fork all pending repos in registry

Requirements:
    - GitHub CLI (gh) installed and authenticated
    - Write access to repolex-forx organization
"""

import argparse
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Configuration
FORK_ORG = "repolex-forx"
PROJECT_ROOT = Path(__file__).parent.parent.parent
REGISTRY_FILE = PROJECT_ROOT / "registry" / "registry.ttl"
SCHEMA_FILE = PROJECT_ROOT / "registry" / "schema.ttl"


def run_gh(args: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command."""
    cmd = ["gh"] + args
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )


def check_gh_auth() -> bool:
    """Verify gh CLI is authenticated."""
    result = run_gh(["auth", "status"])
    return result.returncode == 0


def get_repo_info(repo: str) -> Optional[dict]:
    """Get repository metadata from GitHub API."""
    result = run_gh(["repo", "view", repo, "--json",
                     "name,owner,description,stargazerCount,primaryLanguage,isArchived,isFork"])
    if result.returncode != 0:
        print(f"  Error getting repo info: {result.stderr}")
        return None
    return json.loads(result.stdout)


def check_fork_exists(source_repo: str) -> bool:
    """Check if we already have a fork of this repo."""
    fork_name = source_repo.replace("/", "--")
    result = run_gh(["repo", "view", f"{FORK_ORG}/{fork_name}"])
    return result.returncode == 0


def create_fork(source_repo: str) -> tuple[bool, str]:
    """
    Fork a repository into the repolex-forx org.

    Returns: (success: bool, message: str)
    """
    fork_name = source_repo.replace("/", "--")

    print(f"  Forking {source_repo} → {FORK_ORG}/{fork_name}")

    # gh repo fork <repo> --org <org> --fork-name <name> --clone=false
    result = run_gh([
        "repo", "fork", source_repo,
        "--org", FORK_ORG,
        "--fork-name", fork_name,
        "--clone=false"
    ])

    if result.returncode == 0:
        return True, f"Successfully forked to {FORK_ORG}/{fork_name}"
    else:
        # Check if error is "already exists"
        if "already exists" in result.stderr.lower():
            return True, "Fork already exists"
        return False, result.stderr.strip()


def repo_to_uri(source_repo: str) -> str:
    """Convert repo name to registry URI."""
    safe_name = source_repo.replace("/", "--")
    return f"https://repolex.ai/registry/{safe_name}"


def format_datetime(dt: datetime) -> str:
    """Format datetime for RDF."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_repo_ttl(
    source_repo: str,
    info: dict,
    fork_status: str,
    forked_at: Optional[datetime] = None,
    error: Optional[str] = None,
) -> str:
    """Generate Turtle representation of a tracked repo."""
    uri = repo_to_uri(source_repo)
    owner, name = source_repo.split("/")
    fork_name = source_repo.replace("/", "--")
    now = format_datetime(datetime.now(timezone.utc))

    # Map fork status to ontology term
    status_map = {
        "pending": "forx:forkPending",
        "forked": "forx:forkComplete",
        "failed": "forx:forkFailed",
        "skipped": "forx:forkSkipped",
    }

    lines = [
        f"<{uri}> a forx:TrackedRepo ;",
        f'    forx:sourceOwner "{owner}" ;',
        f'    forx:sourceRepo "{name}" ;',
        f'    forx:sourceFullName "{source_repo}" ;',
        f'    forx:forkFullName "{FORK_ORG}/{fork_name}" ;',
        f"    forx:forkStatus {status_map.get(fork_status, 'forx:forkPending')} ;",
        f"    forx:parseStatus forx:parseNotStarted ;",
        f'    forx:addedAt "{now}"^^xsd:dateTime ;',
    ]

    # Add optional fields
    if info:
        if info.get("stargazerCount"):
            lines.append(f'    forx:stars {info["stargazerCount"]} ;')
        if info.get("primaryLanguage", {}).get("name"):
            lines.append(f'    forx:language "{info["primaryLanguage"]["name"]}" ;')

    if forked_at:
        lines.append(f'    forx:forkedAt "{format_datetime(forked_at)}"^^xsd:dateTime ;')

    if error:
        # Escape quotes in error message
        safe_error = error.replace('"', '\\"').replace("\n", " ")[:200]
        lines.append(f'    forx:lastError "{safe_error}" ;')

    # Close the resource (replace last ; with .)
    lines[-1] = lines[-1].rstrip(" ;") + " ."

    return "\n".join(lines)


def load_registry() -> str:
    """Load existing registry content."""
    if REGISTRY_FILE.exists():
        return REGISTRY_FILE.read_text()
    return ""


def save_registry(content: str):
    """Save registry content."""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(content)


def init_registry():
    """Initialize registry file with prefixes if it doesn't exist."""
    if REGISTRY_FILE.exists():
        return

    header = """@prefix forx: <https://repolex.ai/ont/forx/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# =============================================================================
# REPOLEX-FORX REGISTRY
# =============================================================================
# Auto-generated tracking of all repos in the forking pipeline.
# Last updated: {timestamp}
# =============================================================================

"""
    save_registry(header.format(timestamp=format_datetime(datetime.now(timezone.utc))))


def repo_in_registry(source_repo: str) -> bool:
    """Check if repo is already in registry."""
    uri = repo_to_uri(source_repo)
    content = load_registry()
    return uri in content


def append_to_registry(ttl: str):
    """Append a repo entry to the registry."""
    content = load_registry()
    content += "\n" + ttl + "\n"
    save_registry(content)


def fork_repo(source_repo: str, dry_run: bool = False) -> bool:
    """
    Fork a single repo and update registry.

    Returns True if successful.
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {source_repo}")

    # Check if already in registry
    if repo_in_registry(source_repo):
        print(f"  Already in registry, skipping")
        return True

    # Get repo info
    print(f"  Fetching repo info...")
    info = get_repo_info(source_repo)

    if info is None:
        print(f"  Could not fetch repo info, skipping")
        ttl = generate_repo_ttl(source_repo, {}, "failed", error="Could not fetch repo info")
        if not dry_run:
            append_to_registry(ttl)
        return False

    # Skip archived repos
    if info.get("isArchived"):
        print(f"  Repo is archived, skipping")
        ttl = generate_repo_ttl(source_repo, info, "skipped", error="Archived repository")
        if not dry_run:
            append_to_registry(ttl)
        return False

    # Skip if it's already a fork (we want original repos)
    if info.get("isFork"):
        print(f"  Repo is itself a fork, skipping")
        ttl = generate_repo_ttl(source_repo, info, "skipped", error="Repository is a fork")
        if not dry_run:
            append_to_registry(ttl)
        return False

    # Check if fork already exists
    if check_fork_exists(source_repo):
        print(f"  Fork already exists in {FORK_ORG}")
        ttl = generate_repo_ttl(source_repo, info, "forked", forked_at=datetime.now(timezone.utc))
        if not dry_run:
            append_to_registry(ttl)
        return True

    # Create the fork
    if dry_run:
        print(f"  [DRY RUN] Would fork to {FORK_ORG}/{source_repo.replace('/', '--')}")
        ttl = generate_repo_ttl(source_repo, info, "pending")
        return True

    success, message = create_fork(source_repo)

    if success:
        print(f"  {message}")
        ttl = generate_repo_ttl(source_repo, info, "forked", forked_at=datetime.now(timezone.utc))
        append_to_registry(ttl)
        return True
    else:
        print(f"  Fork failed: {message}")
        ttl = generate_repo_ttl(source_repo, info, "failed", error=message)
        append_to_registry(ttl)
        return False


def load_seed_file(seed_path: str) -> list[str]:
    """Load repos from a seed file (one per line, # comments allowed)."""
    repos = []
    with open(seed_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                repos.append(line)
    return repos


def main():
    parser = argparse.ArgumentParser(
        description="Fork repositories into the repolex-forx organization"
    )
    parser.add_argument(
        "repos",
        nargs="*",
        help="Repository names to fork (e.g., numpy/numpy)"
    )
    parser.add_argument(
        "--seed", "-s",
        help="Path to seed file containing repo names"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without actually forking"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize the registry file"
    )

    args = parser.parse_args()

    # Initialize registry
    init_registry()

    if args.init:
        print(f"Registry initialized at {REGISTRY_FILE}")
        return

    # Check gh auth (only needed for actual forking)
    if not args.dry_run:
        print("Checking GitHub CLI authentication...")
        if not check_gh_auth():
            print("Error: GitHub CLI not authenticated. Run 'gh auth login' first.")
            sys.exit(1)
        print("  Authenticated!\n")

    # Collect repos to process
    repos = list(args.repos)

    if args.seed:
        repos.extend(load_seed_file(args.seed))

    if not repos:
        print("No repos specified. Use positional args or --seed file.")
        parser.print_help()
        sys.exit(1)

    # Process each repo
    print(f"Processing {len(repos)} repos...")

    success_count = 0
    fail_count = 0

    for repo in repos:
        if fork_repo(repo, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"Complete! {success_count} succeeded, {fail_count} failed")
    print(f"Registry: {REGISTRY_FILE}")


if __name__ == "__main__":
    main()
