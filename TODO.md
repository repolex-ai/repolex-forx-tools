# TODO

## Version Discovery
- [ ] Auto-detect and handle multiple versioning schemes (MUST BE FULLY AUTOMATIC)
  - Current: Only strict semver (X.Y.Z)
  - Date-based: `2025.01.31`, `2026.02.25` (e.g., certifi)
  - Prefixed: `v1.0.1`, `release-1.0`
  - CalVer: `2025.1`, `25.3.1`
  - **Solution**: Auto-detect versioning pattern from tags, use heuristics
  - **Fallback**: If no pattern detected, parse all tags (with smart sampling/limiting)
  - **Constraint**: ZERO manual configuration - system runs nonstop, unsupervised

## Repos Without Version Tags
- [ ] Parse repos with zero tags, but throttle to avoid waste (MUST BE FULLY AUTOMATIC)
  - **Problem**: Repos like lexq have no version tags - currently skipped entirely
  - **Solution**: Parse HEAD commit of default branch (main/master)
  - **Throttling**: Only re-parse if >7 days since last parse AND commit SHA changed
  - **Manifest additions**:
    - `head_commit_sha`: Track last parsed HEAD
    - `head_last_parsed`: Date of last HEAD parse
  - **Benefit**: Gets repos into the system even without tags
  - **Constraint**: Must not spam parsing on every commit - weekly is enough
