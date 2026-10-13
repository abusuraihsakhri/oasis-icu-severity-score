# OASIS ICU Severity Score

Reference implementation of the **Oxford Acute Severity of Illness Score (OASIS)** for adult ICU research. Uses ten components derived from observations during the first 24 hours of an ICU stay. Includes a zero-build browser calculator, de-identified CSV batch processing, and Python CLI. The separate multi-worker supervisor is a **demonstration**, not a clinical OASIS inference or treatment system.

## Browser application

The static site lives in [web/index.html](web/index.html) and is designed for GitHub Pages. It calculates scores and processes CSV files entirely in-browser, without transmitting records to a server. No login, cookies, or analytics are used. Do **not** enter names, MRNs, or other identifiable patient information.

**Clinical limitation:** OASIS is a prognostic score derived from ICU cohorts. It is not an intervention threshold, diagnosis, validated triage directive, or substitute for clinical judgment. The optional estimated in-hospital mortality uses the original cohort equation and **requires external/local validation and calibration**. The app does not automatically obtain measurements from clinical records.

## Scoring inputs

All required; extrema refer to the **first ICU day**:

| Field | Unit / interpretation |
|---|---|
| age | Adult years (18–120 supported) |
| pre_icu_los_hours | Hours from hospital admission until ICU admission |
| gcs_min | Lowest Glasgow Coma Scale, 3–15 |
| heart_rate_min / heart_rate_max | Beats/min |
| map_min / map_max | Mean arterial pressure, mmHg |
| respiratory_rate_min / respiratory_rate_max | Breaths/min |
| temperature_min / temperature_max | Celsius |
| urine_output_ml | Total urine output during first ICU 24 hours, mL |
| mechanically_ventilated | Whether ventilated during first ICU day, yes/no |
| elective_surgery | Whether admitted after elective surgery, yes/no |

Missing, nonfinite, and inconsistent values are rejected rather than silently treated as normal. The clinical component point weights and precedence follow [MIT-LCP's MIMIC-IV OASIS reference SQL](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts_postgres/score/oasis.sql), including original-cohort mortality expression `1 / (1 + exp(-(-6.1746 + 0.1275 * score)))`. Small differences from other published tables may reflect rounded breakpoints.

## Use locally

Open `web/index.html` in a modern browser; all scripts are relative and work without a build step. The sample form contains **synthetic example inputs**. For batch scoring, select a CSV matching [sample.csv](sample.csv), optionally with a non-identifying `record_id`. A 5 MB file-size limit applies to browser uploads.

Python 3.10 or newer:

```bash
python oasis_score.py single \
  --age 40 --pre-icu-los-hours 8 --gcs-min 15 \
  --heart-rate-min 70 --heart-rate-max 88 \
  --map-min 80 --map-max 90 \
  --respiratory-rate-min 16 --respiratory-rate-max 20 \
  --temperature-min 36.4 --temperature-max 36.8 \
  --urine-output-ml 3000 \
  --mechanically-ventilated no --elective-surgery yes

python oasis_score.py batch -i sample.csv -o results.csv
```

The Python scorer requires only the standard library. The distinct demo FastAPI/supervisor uses dependencies from `requirements.txt` and a **random** `AUDIT_SECRET_KEY` (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`). It can be launched with `python cli.py serve` after installing dependencies or with Docker Compose; see `.env.example`. Demo API: `/health`, `/metrics` (Prometheus text), `/api/audit`, `/api/chat`, `/api/audit/logs`. **Do not expose the demo endpoints to an untrusted network without authentication, HTTPS, and additional security controls.** Logs are in-memory, not persistent.

The demo supervisor's heuristic alerts, simulated chat responses, metrics, and HMAC chain are **not** a clinical safety certification, HIPAA de-identification mechanism, or medical risk stratification.

## Tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q
node --check web/oasis.js
node --check web/app.js
node --test web/oasis.test.cjs
```

CI covers Python 3.10–3.12 and Node.js 22. The static application needs no Python-in-the-browser runtime, as its small numeric algorithm is directly implemented in JavaScript and independently tested.

## Technology and privacy

Python standard library; optional FastAPI/Pydantic/Uvicorn for demo endpoints; plain HTML/CSS/JavaScript browser calculator. Supports current Chromium, Firefox, and Safari with modern JavaScript and File APIs. Static/browser operations do not transmit or store values. Python CLI operates on locally provided files; users are responsible for secure file handling. No guarantee of HIPAA compliance is made.

## References and license

- Johnson AEW, Kramer AA, Clifford GD. *A new severity of illness scale using a subset of acute physiology and chronic health evaluation data elements shows comparable predictive accuracy*. Critical Care Medicine. 2013;41(7):1711–1718.
- [MIT-LCP OASIS SQL implementation](https://github.com/MIT-LCP/mimic-code/blob/main/mimic-iv/concepts_postgres/score/oasis.sql)
- [MIT License](LICENSE)
