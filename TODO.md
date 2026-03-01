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
