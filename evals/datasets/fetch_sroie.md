# Fetch ICDAR SROIE raw data (optional)

Fixtures under `samples/sroie/` and `evals/gold/sroie/` are already committed for offline CI.

To regenerate from the full public pack:

```bash
git clone --depth 1 https://github.com/zzzDavid/ICDAR-2019-SROIE.git ~/.cache/sroie-repo
cd /path/to/clearance
PYTHONPATH=. python -c "from evals.datasets.sroie_loader import load_sroie; print(len(load_sroie(50, cache=False)))"
python evals/write_real_report.py
```

Attribution: ICDAR 2019 SROIE challenge; packaging via zzzDavid/ICDAR-2019-SROIE (MIT).
