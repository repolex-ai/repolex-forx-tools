#!/usr/bin/env python3
"""
Update manifest after successful parse.
Marks a tag as parsed and updates stats.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

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


def mark_parsed(org_repo, tag, commit_sha, storage_repo=None):
    """
    Mark a tag as successfully parsed.
    """
    manifest = load_manifest()

    if org_repo not in manifest["repos"]:
        print(f"❌ Repo {org_repo} not in manifest", file=sys.stderr)
        sys.exit(1)

    repo_data = manifest["repos"][org_repo]

    # Check if already parsed
    parsed_tags = {pt["tag"] for pt in repo_data["parsed_tags"]}
    if tag in parsed_tags:
        print(f"ℹ️  Tag {tag} already marked as parsed", file=sys.stderr)
        return

    # Generate storage repo name if not provided
    if storage_repo is None:
        storage_repo = f"repolex-forx/{org_repo.replace('/', '--')}"

    # Add to parsed_tags
    entry = {
        "tag": tag,
        "commit_sha": commit_sha,
        "parsed_at": datetime.utcnow().strftime("%Y-%m-%d"),
        "storage_repo": storage_repo,
        "deps_graph": None,  # Will be populated by LSP enrichment
        "parse_status": "complete"
    }

    repo_data["parsed_tags"].append(entry)
    repo_data["parsed_count"] = len(repo_data["parsed_tags"])
    repo_data["last_parsed"] = entry["parsed_at"]

    save_manifest(manifest)

    print(f"✅ Marked {org_repo}@{tag} as parsed", file=sys.stderr)
    print(f"   Parsed: {repo_data['parsed_count']}/{repo_data['total_tags']}", file=sys.stderr)

    # Check if all tags parsed
    if repo_data["parsed_count"] >= repo_data["total_tags"]:
        print(f"🎉 All tags parsed for {org_repo}!", file=sys.stderr)
        # Output signal for workflow
        print("all_tags_parsed=true")
    else:
        print("all_tags_parsed=false")


def main():
    if len(sys.argv) < 4:
        print("Usage: update_manifest.py <org/repo> <tag> <commit_sha> [storage_repo]")
        print("Example: update_manifest.py numpy/numpy 1.24.0 abc123def456")
        sys.exit(1)

    org_repo = sys.argv[1]
    tag = sys.argv[2]
    commit_sha = sys.argv[3]
    storage_repo = sys.argv[4] if len(sys.argv) > 4 else None

    mark_parsed(org_repo, tag, commit_sha, storage_repo)


if __name__ == "__main__":
    main()
