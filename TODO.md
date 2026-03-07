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

## LSP Dependency Caching for CI/CD
- [ ] Pre-cache multilspy language server dependencies in GitHub Actions (CRITICAL FOR AUTOMATION)
  - **Problem**: First use of each LSP downloads 400MB+ deps **silently** with zero progress output
    - Java (jdtls): 200-300MB (JRE + Eclipse JDT LS + Lombok)
    - Gradle: 115MB
    - IntelliCode: 50MB
    - Other languages have similar deps
  - **Impact**: First aggregate job hangs for ~2 hours downloading, looks stuck
  - **Current behavior**: Downloads to `.venv/lib/python3.13/site-packages/multilspy/language_servers/*/static/`
  - **Solution Options**:
    1. Pre-download and cache LSP deps as GitHub Actions cache
    2. Add progress logging to multilspy (upstream contribution)
    3. Run warm-up step that initializes all LSP servers before main job
  - **For automated forx**: Need language detection → pre-cache only needed LSPs
  - **Languages to support**: Python (jedi), Java (jdtls), JavaScript/TypeScript, Rust, Go, Ruby, C#
  - **Cache strategy**: Hash multilspy version + platform → restore/save cache
  - **Constraint**: MUST work unattended - no manual intervention if new language detected
