#!/usr/bin/env python3
"""
Queue manager for repolex-forx parsing queue.
Manages queue.txt and manifest.json entries.
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
    if not MANIFEST_FILE.exists():
        return {
            "version": "1.0",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "repos": {},
            "stats": {
                "total_repos": 0,
                "total_tags_parsed": 0,
                "total_tags_pending": 0
            }
        }
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


def load_queue():
    """Load queue.txt, filter comments and empty lines"""
    if not QUEUE_FILE.exists():
        return []

    with open(QUEUE_FILE) as f:
        lines = [line.strip() for line in f]
        return [line for line in lines if line and not line.startswith("#")]


def save_queue(repos):
    """Save queue.txt"""
    with open(QUEUE_FILE, "w") as f:
        f.write("# repolex-forx parsing queue\n")
        f.write("# One repo per line: org/repo\n")
        f.write("# Lines starting with # are comments\n")
        f.write("# Empty lines ignored\n\n")
        for repo in repos:
            f.write(repo + "\n")


def add_repo(org_repo: str, priority: int = 1):
    """Add a repo to queue and manifest"""
    manifest = load_manifest()
    queue = load_queue()

    # Add to queue if not present
    if org_repo not in queue:
        queue.append(org_repo)
        save_queue(queue)
        print(f"✅ Added {org_repo} to queue")
    else:
        print(f"ℹ️  {org_repo} already in queue")

    # Add to manifest if not present
    if org_repo not in manifest["repos"]:
        manifest["repos"][org_repo] = {
            "added_at": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": priority,
            "parsed_tags": [],
            "discovered_tags": null,
            "total_tags": 0,
            "parsed_count": 0,
            "last_parsed": None
        }
        save_manifest(manifest)
        print(f"✅ Added {org_repo} to manifest")
    else:
        print(f"ℹ️  {org_repo} already in manifest")


def remove_repo(org_repo: str):
    """Remove a repo from queue (keeps in manifest for history)"""
    queue = load_queue()

    if org_repo in queue:
        queue.remove(org_repo)
        save_queue(queue)
        print(f"✅ Removed {org_repo} from queue")
    else:
        print(f"ℹ️  {org_repo} not in queue")


def add_bulk(file_path: str):
    """Add multiple repos from a seed file"""
    with open(file_path) as f:
        repos = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    for repo in repos:
        add_repo(repo)


def list_queue():
    """List current queue with stats"""
    manifest = load_manifest()
    queue = load_queue()

    print(f"\n📋 Queue Status ({len(queue)} repos)\n")
    print(f"{'Repo':<40} {'Parsed':<15} {'Pending':<15}")
    print("─" * 70)

    for repo in queue:
        if repo in manifest["repos"]:
            data = manifest["repos"][repo]
            parsed = data["parsed_count"]
            total = data["total_tags"] or "?"
            pending = (data["total_tags"] - data["parsed_count"]) if data["total_tags"] else "?"
            print(f"{repo:<40} {parsed:<15} {pending:<15}")
        else:
            print(f"{repo:<40} {'0':<15} {'unknown':<15}")

    print("\n" + "─" * 70)
    print(f"Total: {manifest['stats']['total_tags_parsed']} parsed, {manifest['stats']['total_tags_pending']} pending\n")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  queue_manager.py add <org/repo>")
        print("  queue_manager.py remove <org/repo>")
        print("  queue_manager.py add-bulk <file>")
        print("  queue_manager.py list")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add" and len(sys.argv) >= 3:
        add_repo(sys.argv[2])
    elif command == "remove" and len(sys.argv) >= 3:
        remove_repo(sys.argv[2])
    elif command == "add-bulk" and len(sys.argv) >= 3:
        add_bulk(sys.argv[2])
    elif command == "list":
        list_queue()
    else:
        print("❌ Invalid command")
        sys.exit(1)


if __name__ == "__main__":
    main()
