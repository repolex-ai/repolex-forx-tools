#!/usr/bin/env python3
"""
Discover semantic version tags from a git repository.
Updates manifest with discovered tags.
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from packaging import version

REPO_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = REPO_ROOT / "manifest.json"


def load_manifest():
    """Load manifest.json"""
    with open(MANIFEST_FILE) as f:
        return json.load(f)


def save_manifest(manifest):
    """Save manifest.json atomically"""
    manifest["last_updated"] = datetime.utcnow().isoformat() + "Z"

    # Recalculate stats
    manifest["stats"] = {
        "total_repos": len(manifest["repos"]),
        "total_tags_parsed": sum(r["parsed_count"] for r in manifest["repos"].values()),
        "total_tags_pending": sum(
            (r["total_tags"] - r["parsed_count"]) for r in manifest["repos"].values()
        )
    }

    # Atomic write
    tmp = MANIFEST_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    tmp.rename(MANIFEST_FILE)


def get_all_tags(repo_path):
    """Get all git tags from a repository"""
    result = subprocess.run(
        ["git", "tag", "--list"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def filter_semver_tags(tags):
    """Filter to strict semantic version tags (X.Y.Z)"""
    semver_pattern = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
    filtered = []

    for tag in tags:
        # Strip leading 'v' if present
        clean_tag = tag.lstrip("v")
        if semver_pattern.match(clean_tag):
            filtered.append(clean_tag)

    return filtered


def select_versions_smart(tags):
    """
    Smart selection: Latest patch in each major.minor series.

    Example:
    Input:  ['1.0.0', '1.0.1', '1.0.2', '1.1.0', '2.0.0', '2.0.1']
    Output: ['1.0.2', '1.1.0', '2.0.1']
    """
    by_major_minor = defaultdict(list)

    for tag in tags:
        v = version.parse(tag)
        key = (v.major, v.minor)
        by_major_minor[key].append(tag)

    # Get latest patch for each major.minor
    result = []
    for versions in by_major_minor.values():
        latest = max(versions, key=version.parse)
        result.append(latest)

    # Sort result
    return sorted(result, key=version.parse)


def discover_and_update(org_repo, repo_path):
    """
    Discover versions and update manifest.
    """
    print(f"🔍 Discovering versions for {org_repo}...")

    # Get all tags
    all_tags = get_all_tags(repo_path)
    print(f"  Found {len(all_tags)} total tags")

    # Filter to semver
    semver_tags = filter_semver_tags(all_tags)
    print(f"  Filtered to {len(semver_tags)} semantic version tags")

    if not semver_tags:
        print(f"  ⚠️  No semantic version tags found - marking as discovered with 0 tags")
        selected = []
    else:
        # Smart selection
        selected = select_versions_smart(semver_tags)
        print(f"  Selected {len(selected)} versions (latest patch per minor)")

    # Update manifest
    manifest = load_manifest()

    if org_repo not in manifest["repos"]:
        manifest["repos"][org_repo] = {
            "added_at": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": 1,
            "parsed_tags": [],
            "discovered_tags": None,
            "total_tags": 0,
            "parsed_count": 0,
            "last_parsed": None
        }

    manifest["repos"][org_repo]["discovered_tags"] = selected
    manifest["repos"][org_repo]["total_tags"] = len(selected)

    save_manifest(manifest)

    print(f"  ✅ Updated manifest with {len(selected)} tags")
    return selected


def main():
    if len(sys.argv) < 3:
        print("Usage: discover_versions.py <org/repo> <repo_path>")
        print("Example: discover_versions.py numpy/numpy /tmp/source")
        sys.exit(1)

    org_repo = sys.argv[1]
    repo_path = Path(sys.argv[2])

    if not repo_path.exists():
        print(f"❌ Repository path does not exist: {repo_path}")
        sys.exit(1)

    discovered = discover_and_update(org_repo, repo_path)

    # Output discovered tags (one per line) for workflow consumption
    for tag in discovered:
        print(tag)


if __name__ == "__main__":
    main()
