# Extraction failure gallery

Honest miss list from offline Clearance Bench (mock extractor). Use in interviews: *where it breaks and why HITL exists*.

## Synthetic

- Cases: **50** · micro field acc: **97.5%** · docs with ≥1 miss: **5**

| Case | Missed fields | Gold vendor | Pred total vs gold |
| --- | --- | --- | --- |
| `syn-0000` | total | Quantum Parts LLC | 10000.0 vs 10800.0 |
| `syn-0017` | total | Soylent Foods | 6367.35 vs 6876.74 |
| `syn-0023` | total | Northwind Traders | 1162.17 vs 1149.83 |
| `syn-0034` | total | Initech Services | 6113.9 vs 6603.01 |
| `syn-0046` | total | Quantum Parts LLC | 3816.1 vs 3803.76 |

## SROIE assisted (footer labels present)

- Cases: **50** · micro field acc: **98.0%** · docs with ≥1 miss: **4**

| Case | Missed fields | Gold vendor | Pred total vs gold |
| --- | --- | --- | --- |
| `sroie-012` | vendor | HOME MASTER HARDWARE & ELECTRICAL | 15.9 vs 15.9 |
| `sroie-015` | vendor | HOME MASTER HARDWARE & ELECTRICAL | 15.9 vs 15.9 |
| `sroie-019` | vendor | SHELL ISNI PETRO TRADING | 86.0 vs 86.0 |
| `sroie-050` | vendor | TIMELESS KITCHENETTE SDN BHD | 593.1 vs 593.1 |

## SROIE hard (OCR body only)

- Cases: **50** · micro field acc: **79.5%** · docs with ≥1 miss: **35**

| Case | Missed fields | Gold vendor | Pred total vs gold |
| --- | --- | --- | --- |
| `sroie-hard-000` | vendor, total | BOOK TA .K (TAMAN DAYA) SDN BHD | 0.0 vs 9.0 |
| `sroie-hard-001` | vendor, total | INDAH GIFT & HOME DECO | 0.0 vs 60.3 |
| `sroie-hard-006` | vendor, total | SOON HUAT MACHINERY ENTERPRISE | 0.0 vs 327.0 |
| `sroie-hard-009` | vendor, total | GERBANG ALAF RESTAURANTS SDN BHD | 11.0 vs 26.6 |
| `sroie-hard-026` | vendor, total | TED HENG STATIONERY & BOOKS | 144.68 vs 153.35 |
| `sroie-hard-029` | vendor, total | C W KHOO HARDWARE SDN BHD | 0.0 vs 21.2 |
| `sroie-hard-002` | vendor | MR D.I.Y. (JOHOR) SDN BHD | 33.92 vs 33.9 |
| `sroie-hard-003` | vendor | YONGFATT ENTERPRISE | 80.91 vs 80.9 |
| `sroie-hard-004` | vendor | MR D.I.Y. (M) SDN BHD | 30.91 vs 30.9 |
| `sroie-hard-005` | vendor | ABC HO TRADING | 31.0 vs 31.0 |
| `sroie-hard-007` | vendor | S.H.H. MOTOR (SUNGAI RENGIT) SDN. BHD. | 20.0 vs 20.0 |
| `sroie-hard-008` | total | PERNIAGAAN ZHENG HUI | 106.1 vs 112.45 |

## Notes

- **Assisted SROIE** includes labeled `Vendor:` / `Total:` lines — high scores are partly format-assisted.
- **Hard SROIE** strips those lines; invoice # is not scored (synthetic `SROIE-*` ids only exist in the footer).
- Mock rules fail on noisy OCR vendor names and multi-total receipts → policy/HITL is the product.

Regenerate:

```bash
python evals/write_failures.py
python evals/write_real_report.py
```
