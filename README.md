# repolex-forx-tools

Orchestration tools for managing the **repolex-forx** GitHub organization—where we fork every open source repo and parse it into RDF.

## The Vision

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPEN SOURCE UNIVERSE                          │
│  numpy/numpy    pandas-dev/pandas    psf/requests    ...        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ fork
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    repolex-forx org                              │
│  numpy--numpy    pandas-dev--pandas    psf--requests    ...     │
│     │                  │                     │                   │
│     └──────────────────┴─────────────────────┘                  │
│                    GitHub Actions                                │
│                    (parse → RDF)                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ upload
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    repolex.ai                                    │
│              The Semantic Index of Open Source                   │
│                    (SPARQL endpoint)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Install with uv
uv sync

# Initialize the registry
uv run forx-fork --init

# Fork a single repo
uv run forx-fork numpy/numpy

# Fork all repos in a seed list
uv run forx-fork --seed seeds/python-core.txt

# Dry run (see what would happen)
uv run forx-fork --dry-run psf/requests

# Check status
uv run forx-status
uv run forx-status --forked
uv run forx-status --pending
uv run forx-status --languages
```

## Requirements

- [uv](https://github.com/astral-sh/uv) for Python package management
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- Write access to the `repolex-forx` organization

## Project Structure

```
repolex-forx-tools/
├── pyproject.toml              # Project config (uv/pip)
├── src/
│   └── repolex_forx_tools/
│       ├── __init__.py
│       ├── fork.py             # Main forking automation
│       └── status.py           # SPARQL-powered status queries
├── registry/
│   ├── schema.ttl              # RDF ontology for tracking
│   └── registry.ttl            # The actual registry (auto-populated)
└── seeds/
    └── python-core.txt         # Foundational Python repos
```

## Naming Convention

Source repos are forked with `--` replacing `/`:

| Source | Fork |
|--------|------|
| `numpy/numpy` | `repolex-forx/numpy--numpy` |
| `pandas-dev/pandas` | `repolex-forx/pandas-dev--pandas` |
| `psf/requests` | `repolex-forx/psf--requests` |

## Registry Schema

The registry is RDF (Turtle format), queryable with SPARQL:

```sparql
# What repos still need to be forked?
SELECT ?repo WHERE {
    ?repo a forx:TrackedRepo ;
          forx:forkStatus forx:forkPending .
}

# What's been parsed successfully?
SELECT ?repo ?parsedAt WHERE {
    ?repo forx:parseStatus forx:parseComplete ;
          forx:lastParsed ?parsedAt .
}

# Total stars across all tracked repos?
SELECT (SUM(?stars) AS ?totalStars) WHERE {
    ?repo forx:stars ?stars .
}
```

## Development

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check src/
```

## License

MIT
