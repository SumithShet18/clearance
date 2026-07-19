# Clearance Bench Report

Dual-track evaluation (research-backed).

## Track A — Synthetic invoices (reproducible, no PII)

- Cases: **50**
- Micro field accuracy: **97.5%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 90.0% |
| vendor | 100.0% |

### Full agent pipeline (subset)

- Cases: **25**
- Auto-acted (STP proxy): **52.0%**
- Needs review (HITL): **48.0%**
- Status counts: `{'needs_review': 12, 'acted': 13}`

## Track B — CORD v2 real receipts

Source: HuggingFace `naver-clova-ix/cord-v2`. Text renders are built from public ground-truth annotations (honest offline path).

- Cases: **25**
- Micro field accuracy: **100.0%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 100.0% |
| vendor | 100.0% |

## Notes

- Synthetic includes stress cases (noise / missing invoice # / math drift).
- CORD track validates totals/fields from public receipt labels without shipping multi-GB images.
- Default mock extractor; optional `CLEARANCE_MODE=llm` for vision.
- One-click cloud deploy: see README Render button.

