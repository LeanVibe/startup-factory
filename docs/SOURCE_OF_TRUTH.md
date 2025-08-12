# Single Source of Truth

This repository’s single source of truth is the combination of the following core docs. Treat them as canonical and keep them in sync with the code and UX.

- README.md — founder-facing overview and usage
- CLAUDE.md — developer/system guidance and architecture
- PRODUCTION_SETUP.md — production setup and ops notes
- TRANSFORMATION_COMPLETE.md — transformation summary
- FINAL_TRANSFORMATION_REPORT.md — detailed results and metrics
- docs/NAV_INDEX.md — auto-generated navigation (do not edit by hand)

When updating behavior, UX, or architecture:
- Update README.md and CLAUDE.md accordingly
- If substantial, reflect in TRANSFORMATION_COMPLETE.md and FINAL_TRANSFORMATION_REPORT.md
- Re-run the index generator to refresh docs/NAV_INDEX.md and docs/nav_index.json
