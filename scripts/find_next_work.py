#!/usr/bin/env python3
"""
Find next parsing work from queue and manifest.
Outputs GitHub Actions variables for workflow.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
QUEUE_FILE = REPO_ROOT / "queue.txt"
MANIFEST_FILE = REPO_ROOT / "manifest.json"


def load_manifest():
    """Load manifest.json"""
    with open(MANIFEST_FILE) as f:
        return json.load(f)


def load_queue():
    """Load queue.txt, filter comments and empty lines"""
    with open(QUEUE_FILE) as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line and not line.startswith("#")]


def find_next_repo(queue, manifest):
    """
    Find next repo to parse using round-robin strategy.
    Prioritize repos that:
    1. Have undiscovered tags (need version discovery)
    2. Have unparsed tags
    3. Haven't been parsed recently
    """
    repos_with_work = []

    for org_repo in queue:
        if org_repo not in manifest["repos"]:
            # New repo - needs version discovery
            repos_with_work.append((org_repo, None, "new"))
            continue

        data = manifest["repos"][org_repo]

        # Check if we need to discover versions
        if data["discovered_tags"] is None:
            repos_with_work.append((org_repo, data.get("last_parsed"), "discover"))
            continue

        # Check if there are unparsed tags
        if data["parsed_count"] < data["total_tags"]:
            repos_with_work.append((org_repo, data.get("last_parsed"), "parse"))

    if not repos_with_work:
        return None

    # Sort by last_parsed (None comes first, then oldest)
    def sort_key(item):
        _, last_parsed, work_type = item
        if last_parsed is None:
            return (0, "")  # Never parsed - highest priority
        return (1, last_parsed)

    repos_with_work.sort(key=sort_key)
    return repos_with_work[0][0]


def find_next_tag(org_repo, manifest):
    """
    Find next unparsed tag for a repo.
    Returns None if version discovery needed.
    """
    if org_repo not in manifest["repos"]:
        return None

    data = manifest["repos"][org_repo]

    # Check if discovery needed
    if data["discovered_tags"] is None:
        return None

    # Find first unparsed tag
    parsed_tags = {pt["tag"] for pt in data["parsed_tags"]}
    for tag in data["discovered_tags"]:
        if tag not in parsed_tags:
            return tag

    return None


def main():
    """
    Output GitHub Actions variables:
    - repo=org/repo
    - tag=x.y.z (or empty if discovery needed)
    - storage_repo=repolex-forx/org--repo
    - needs_discovery=true/false
    """
    try:
        manifest = load_manifest()
        queue = load_queue()
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        # Output empty values so workflow skips
        print("repo=")
        print("tag=")
        print("storage_repo=")
        print("needs_discovery=false")
        sys.exit(0)

    # Find next work
    next_repo = find_next_repo(queue, manifest)

    if next_repo is None:
        print(f"ℹ️  No work found in queue", file=sys.stderr)
        print("repo=")
        print("tag=")
        print("storage_repo=")
        print("needs_discovery=false")
        sys.exit(0)

    # Find next tag
    next_tag = find_next_tag(next_repo, manifest)

    # Generate storage repo name
    storage_repo = f"repolex-forx/{next_repo.replace('/', '--')}"

    # Output GitHub Actions variables
    print(f"repo={next_repo}")
    print(f"tag={next_tag or ''}")
    print(f"storage_repo={storage_repo}")
    print(f"needs_discovery={'true' if next_tag is None else 'false'}")

    # Log to stderr for visibility
    if next_tag:
        print(f"📦 Next work: {next_repo}@{next_tag}", file=sys.stderr)
    else:
        print(f"🔍 Next work: {next_repo} (discovery needed)", file=sys.stderr)


if __name__ == "__main__":
    main()
