# VERIDIS API - CSRD Analysis Engine

Backend Python MVP for the VERIDIS CSRD analysis pipeline.

## Scope

- SQLAlchemy 2.0 models for companies, reports, ESRS requirements, answers and gaps.
- Parsing engine for PDF, DOCX, XLSX and CSV with graceful fallback.
- OpenAI ESG client with deterministic fallback for tests and degraded mode.
- Analysis orchestrator with explicit pipeline steps and retry backoff.
- Auditable scoring engine.
- Versioned gap detector rules.
- Unit tests for scoring and gap detection.

## Install

```bash
cd apps/api
python -m pip install -e ".[dev]"
```

## Tests

```bash
cd apps/api
pytest
```

## Notes

The OpenAI integration is optional at runtime. If no API key or SDK is available,
the extraction layer returns deterministic heuristic results and marks them with
`fallback_heuristique`.

Suggestions after main code:

- Add Prompt #6 seed data for the 12 ESRS standards before using this engine on real reports.
- Add a persistent prompt/version table before external audits.
- Add a controlled evaluation corpus of public French RSE reports to track extraction quality.

