# Automated Parsing System

**Date**: 2026-02-21
**Status**: Operational (MVP)

## Overview

The repolex-forx automated parsing system provides continuous parsing and storage of open source repositories using GitHub Actions. Each repository gets its own storage repo that runs daily checks for new releases and parses them incrementally.

## Architecture

```
┌─────────────────┐
│  Source Repo    │ jmespath/jmespath.py (external)
│  (GitHub)       │
└────────┬────────┘
         │
         │ daily check for new tags
         ▼
┌─────────────────┐
│  Storage Repo   │ repolex-forx/jmespath--jmespath.py
│  (GitHub)       │
│                 │ • manifest.json (tracks parsed tags)
│                 │ • .github/workflows/parse-repo.yml
│                 │ • files/{org}/{repo}/*.nq.gz
└─────────────────┘
         ▲
         │ GitHub Actions (daily cron)
         │
         ├─ 1. Clone source repo
         ├─ 2. Check manifest for unparsed tags
         ├─ 3. Parse oldest unparsed tag
         ├─ 4. Generate .nq.gz graph files
         ├─ 5. Commit graphs back to storage repo
         └─ 6. Update manifest
```

## Components

### 1. Storage Repository Structure

Each source repo gets a public storage repo in the `repolex-forx` GitHub organization.

**Naming convention**: `{source-org}--{source-repo}`
**Example**: `repolex-forx/jmespath--jmespath.py`

**Files**:
```
jmespath--jmespath.py/
├── manifest.json                   # Tracks which tags have been parsed
├── .github/workflows/
│   └── parse-repo.yml             # Daily parsing workflow
└── files/jmespath/jmespath.py/
    ├── blob/{hash}.nq.gz          # Content-addressed AST blobs (gzipped)
    ├── commit/commit.nq           # Git commit metadata
    ├── tag/tag.nq                 # Git tags
    ├── branch/branch.nq           # Git branches
    ├── filetree/{sha}.nq          # File tree per commit
    └── aggregate/ast/{sha}.nq.gz  # Aggregate AST with RDFS reasoning (gzipped)
```

### 2. manifest.json

Tracks parsing progress:

```json
{
  "source": "jmespath/jmespath.py",
  "parsed_tags": [
    {
      "tag": "0.9.0",
      "commit_sha": "2812594e69d43098ef60f81f4efc404c071b0418",
      "parsed_at": "2026-02-21"
    }
  ]
}
```

### 3. GitHub Actions Workflow

**Trigger**: Daily at 6am UTC + manual `workflow_dispatch`

**Process**:
1. **Checkout storage repo** (with write permissions)
2. **Clone source repo** + fetch all tags
3. **Read manifest** → get list of already-parsed tags
4. **Find next tag** → oldest unparsed release tag (semantic versioning: X.Y.Z)
5. **Checkout source at tag**
6. **Set `REPOLEX_HOME`** → storage repo path
7. **Run `repolex parse`** → generates blob files
8. **Run `repolex aggregate`** → generates aggregate AST
9. **Update manifest.json** → add newly parsed tag
10. **Commit and push** → graphs + updated manifest

**Authentication**:
- Uses organization secret `REPOLEX_PAT` (Personal Access Token with `repo` scope)
- Allows cloning private `repolex-ai/repolex-parser-py` during `uv tool install`

## File Compression

All RDF files use gzip compression to stay under GitHub's 100 MB file size limit:

- **Blob files**: `{hash}.nq.gz` (~90% compression)
- **Aggregate files**: `{sha}.nq.gz` (~95% compression)
  - Example: 232 MB → 11 MB for jmespath.py

Compression ratios scale well:
- **Source repos up to ~400 MB** can be parsed and stored
- Covers 95%+ of interesting open source projects

## Current Limitations

### What Works
- ✅ Incremental parsing (one tag per day)
- ✅ Content-addressed blobs (reuse across tags)
- ✅ Automatic tag discovery
- ✅ Gzip compression
- ✅ Manifest tracking
- ✅ Daily cron execution

### Future Work
- ⏳ **Multilspy enrichment** (LSP-based type info) - not yet integrated
- ⏳ **Aggregate optimization** - current 200MB+ uncompressed size is temporary
- ⏳ **Parallel parsing** - currently processes one tag at a time
- ⏳ **Error handling** - parse failures don't block future runs
- ⏳ **Monitoring** - no alerts for failed runs yet

## Tools

### `forx-create`

Create a new storage repo:

```bash
forx-create jmespath/jmespath.py
```

**What it does**:
1. Creates `repolex-forx/{org}--{repo}` as a public repo
2. Initializes with `manifest.json`, `README.md`, `.gitignore`
3. Copies workflow template from `repolex-forx-tools/.github/workflows/parse-repo.yml`
4. Updates `SOURCE_ORG` and `SOURCE_REPO` env vars
5. Commits and pushes initial setup

### `forx-fork` (legacy)

Original tool for creating actual GitHub forks. **Not used** in current system - we use plain public repos instead.

### `forx-status`

Query parsing status via SPARQL (references `registry/registry.ttl`). Currently tracks forked repos, but will need updates for new storage repo model.

## Setup: New Repository

### Prerequisites
1. `REPOLEX_PAT` secret set at organization level (`repolex-forx`)
2. PAT has `repo` scope for accessing private `repolex-parser-py`
3. `forx-create` tool installed: `uv tool install -e .`

### Steps

```bash
# 1. Create storage repo
forx-create numpy/numpy

# 2. Trigger first parse (or wait for daily cron)
gh workflow run parse-repo.yml --repo repolex-forx/numpy--numpy

# 3. Monitor progress
gh run watch --repo repolex-forx/numpy--numpy

# 4. Check results
gh repo view repolex-forx/numpy--numpy
```

## Performance

**jmespath.py v0.9.0**:
- Source: 1.8 MB (62 source files)
- Parse time: ~2 minutes (GitHub Actions)
- Output: 6.2 MB blobs + 11 MB aggregate (compressed)
- Total: ~17 MB per tag

**Scaling estimate**:
- Small repos (<10 MB): ~3-5 min per tag
- Medium repos (10-50 MB): ~5-10 min per tag
- Large repos (50-100 MB): ~10-20 min per tag

## Known Issues

1. **Oxigraph files committed** - Current workflow commits `oxigraph/` directory (transient query cache). Should add `.gitignore` or clear before commit.

2. **No failure recovery** - If parsing fails midway, manifest isn't updated. Next run will retry the same tag.

3. **Single-threaded** - Parses one file at a time. Could parallelize blob parsing.

4. **No deduplication** - If the same file appears in multiple tags (same blob hash), we store it once (content-addressed) but the aggregate is regenerated for each tag.

## References

- **repolex parser**: https://github.com/repolex-ai/repolex-parser-py (private)
- **lexq query tool**: https://github.com/repolex-ai/lexq
- **Workflow template**: `.github/workflows/parse-repo.yml`
- **forx-create tool**: `src/repolex_forx_tools/create_storage.py`

## Changelog

### 2026-02-21
- Initial MVP operational
- Gzip compression for all RDF files
- Daily cron + manual trigger support
- Organization-level `REPOLEX_PAT` secret
- First test repo: `jmespath--jmespath.py`
