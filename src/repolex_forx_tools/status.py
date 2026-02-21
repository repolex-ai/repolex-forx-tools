#!/usr/bin/env python3
"""
status.py - Query the repolex-forx registry

Usage:
    python status.py                    # Show summary
    python status.py --pending          # List repos pending fork
    python status.py --forked           # List forked repos
    python status.py --failed           # List failed repos
    python status.py --query "SPARQL"   # Run custom SPARQL query

Requirements:
    pip install rdflib
"""

import argparse
from pathlib import Path

try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF, RDFS, XSD
except ImportError:
    print("Error: rdflib not installed. Run: pip install rdflib")
    exit(1)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
REGISTRY_FILE = PROJECT_ROOT / "registry" / "registry.ttl"
SCHEMA_FILE = PROJECT_ROOT / "registry" / "schema.ttl"

# Namespace
FORX = Namespace("https://repolex.ai/ont/forx/")


def load_graph() -> Graph:
    """Load the registry and schema into an RDF graph."""
    g = Graph()
    g.bind("forx", FORX)
    g.bind("xsd", XSD)

    if SCHEMA_FILE.exists():
        g.parse(SCHEMA_FILE, format="turtle")

    if REGISTRY_FILE.exists():
        g.parse(REGISTRY_FILE, format="turtle")
    else:
        print(f"Warning: Registry file not found at {REGISTRY_FILE}")
        print("Run 'python fork.py --init' to create it.")

    return g


def summary(g: Graph):
    """Print summary statistics."""
    query = """
    SELECT
        (COUNT(?repo) AS ?total)
        (SUM(IF(?forkStatus = forx:forkComplete, 1, 0)) AS ?forked)
        (SUM(IF(?forkStatus = forx:forkPending, 1, 0)) AS ?pending)
        (SUM(IF(?forkStatus = forx:forkFailed, 1, 0)) AS ?failed)
        (SUM(IF(?forkStatus = forx:forkSkipped, 1, 0)) AS ?skipped)
        (SUM(IF(?parseStatus = forx:parseComplete, 1, 0)) AS ?parsed)
        (SUM(?stars) AS ?totalStars)
    WHERE {
        ?repo a forx:TrackedRepo ;
              forx:forkStatus ?forkStatus ;
              forx:parseStatus ?parseStatus .
        OPTIONAL { ?repo forx:stars ?stars }
    }
    """

    results = list(g.query(query))
    if results:
        row = results[0]
        total = int(row.total or 0)
        forked = int(row.forked or 0)
        pending = int(row.pending or 0)
        failed = int(row.failed or 0)
        skipped = int(row.skipped or 0)
        parsed = int(row.parsed or 0)
        total_stars = int(row.totalStars or 0)

        print("=" * 50)
        print("REPOLEX-FORX REGISTRY STATUS")
        print("=" * 50)
        print(f"Total tracked repos:  {total}")
        print(f"  Forked:             {forked}")
        print(f"  Pending:            {pending}")
        print(f"  Failed:             {failed}")
        print(f"  Skipped:            {skipped}")
        print("-" * 50)
        print(f"Parsed successfully:  {parsed}")
        print(f"Total stars:          {total_stars:,}")
        print("=" * 50)
    else:
        print("No repos in registry yet.")


def list_by_status(g: Graph, status: str):
    """List repos by fork status."""
    status_uri = {
        "pending": "forx:forkPending",
        "forked": "forx:forkComplete",
        "failed": "forx:forkFailed",
        "skipped": "forx:forkSkipped",
    }.get(status)

    if not status_uri:
        print(f"Unknown status: {status}")
        return

    query = f"""
    SELECT ?source ?fork ?stars ?language ?error
    WHERE {{
        ?repo a forx:TrackedRepo ;
              forx:forkStatus {status_uri} ;
              forx:sourceFullName ?source ;
              forx:forkFullName ?fork .
        OPTIONAL {{ ?repo forx:stars ?stars }}
        OPTIONAL {{ ?repo forx:language ?language }}
        OPTIONAL {{ ?repo forx:lastError ?error }}
    }}
    ORDER BY DESC(?stars)
    """

    results = list(g.query(query))
    print(f"\nRepos with status '{status}': {len(results)}\n")

    for row in results:
        stars = f"({row.stars})" if row.stars else ""
        lang = f"[{row.language}]" if row.language else ""
        print(f"  {row.source} {stars} {lang}")
        if row.error:
            print(f"    Error: {row.error}")

    if not results:
        print("  (none)")


def list_unparsed(g: Graph):
    """List repos that have been forked but not yet parsed."""
    query = """
    SELECT ?source ?fork
    WHERE {
        ?repo a forx:TrackedRepo ;
              forx:forkStatus forx:forkComplete ;
              forx:parseStatus forx:parseNotStarted ;
              forx:sourceFullName ?source ;
              forx:forkFullName ?fork .
    }
    """

    results = list(g.query(query))
    print(f"\nForked but not yet parsed: {len(results)}\n")

    for row in results:
        print(f"  {row.source} → {row.fork}")


def run_query(g: Graph, sparql: str):
    """Run a custom SPARQL query."""
    try:
        results = g.query(sparql)
        for row in results:
            print(row)
    except Exception as e:
        print(f"Query error: {e}")


def by_language(g: Graph):
    """Group repos by language."""
    query = """
    SELECT ?language (COUNT(?repo) AS ?count) (SUM(?stars) AS ?totalStars)
    WHERE {
        ?repo a forx:TrackedRepo ;
              forx:language ?language .
        OPTIONAL { ?repo forx:stars ?stars }
    }
    GROUP BY ?language
    ORDER BY DESC(?count)
    """

    results = list(g.query(query))
    print("\nRepos by language:\n")

    for row in results:
        stars = int(row.totalStars or 0)
        print(f"  {row.language}: {row.count} repos ({stars:,} stars)")


def main():
    parser = argparse.ArgumentParser(
        description="Query the repolex-forx registry"
    )
    parser.add_argument("--pending", action="store_true", help="List pending repos")
    parser.add_argument("--forked", action="store_true", help="List forked repos")
    parser.add_argument("--failed", action="store_true", help="List failed repos")
    parser.add_argument("--skipped", action="store_true", help="List skipped repos")
    parser.add_argument("--unparsed", action="store_true", help="List forked but unparsed repos")
    parser.add_argument("--languages", action="store_true", help="Group by language")
    parser.add_argument("--query", "-q", help="Run custom SPARQL query")

    args = parser.parse_args()

    g = load_graph()

    if args.query:
        run_query(g, args.query)
    elif args.pending:
        list_by_status(g, "pending")
    elif args.forked:
        list_by_status(g, "forked")
    elif args.failed:
        list_by_status(g, "failed")
    elif args.skipped:
        list_by_status(g, "skipped")
    elif args.unparsed:
        list_unparsed(g)
    elif args.languages:
        by_language(g)
    else:
        summary(g)


if __name__ == "__main__":
    main()
