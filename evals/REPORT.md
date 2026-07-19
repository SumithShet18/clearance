# Clearance Bench Report

Multi-track evaluation on **synthetic stress data** and **public real receipt datasets**.

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

## Track B — ICDAR 2019 SROIE (assisted labels)

- Cases: **50**
- Micro field accuracy: **98.0%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 100.0% |
| vendor | 92.0% |

Source: [zzzDavid/ICDAR-2019-SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) public labels (`company`, `date`, `total`) + OCR box transcripts.
This track includes an explicit labeled footer (`Vendor:` / `Total:`) — **format-assisted**; use Track B2 for honest OCR difficulty.

## Track B2 — SROIE hard (OCR body only)

- Cases: **50**
- Micro field accuracy: **79.5%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 52.0% |
| vendor | 66.0% |

Same receipts with **assist footer stripped**. Invoice # not scored (synthetic `SROIE-*` ids only exist in the footer).
Failure gallery: [results/failures.md](results/failures.md).

## Track C — CORD v2 receipt fixtures

- Cases: **25**
- Micro field accuracy: **100.0%**

| Field | Accuracy |
| --- | ---: |
| currency | 100.0% |
| invoice_number | 100.0% |
| total | 100.0% |
| vendor | 100.0% |

Source: HuggingFace `naver-clova-ix/cord-v2` ground-truth renders (committed fixtures).

## How to read these numbers

- **Field accuracy** measures extraction vs gold labels (vendor, invoice #, total, currency).
- **Assisted vs hard SROIE:** assisted is demo-friendly; hard is the credibility track.
- **STP / HITL** measures the *agent policy graph*, not OCR alone — ~50% auto is intentional risk control.
- Default extractor is **mock/rules** (offline). Optional `CLEARANCE_MODE=llm` for multimodal models.
- These results support a **portfolio / production-pattern** claim, not “beats Vic.ai SOTA.”

## Reproduce

```bash
python evals/run_benchmark.py --source sroie --limit 50
python evals/run_benchmark.py --source sroie-hard --limit 50
python evals/run_benchmark.py --source synthetic --limit 50 --pipeline
python evals/write_real_report.py
python evals/write_failures.py
```
