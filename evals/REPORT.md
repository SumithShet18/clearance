# Clearance Bench Report

Generated: `2026-07-19T09:55:06.913461+00:00`

## Extraction (per-field)

- Cases: **50**
- Micro field accuracy: **100.0%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 100.0% |
| vendor | 100.0% |

## Full agent pipeline (subset)

- Cases: **25**
- Auto-acted (STP proxy): **56.0%**
- Needs review (HITL): **44.0%**
- Status counts: `{'needs_review': 11, 'acted': 14}`

## Notes

- Synthetic invoices are generated with fixed seed (reproducible, no PII).
- CORD track is optional (`--source cord`) when HuggingFace `datasets` is available.
- Mock extractor mode is default; set `CLEARANCE_MODE=llm` + API key for multimodal.
