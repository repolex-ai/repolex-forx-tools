# TODO

## Version Discovery
- [ ] Fix for repos that don't use semantic versioning for tags
  - Some repos use date-based versioning (e.g., certifi uses `2025.01.31`, `2026.02.25`)
  - Some repos use other formats (e.g., `v1.0`, `release-1.0`)
  - Current `discover_versions.py` only filters for strict semver (X.Y.Z)
  - Need to support multiple versioning schemes or make filtering configurable
