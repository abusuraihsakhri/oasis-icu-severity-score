#!/usr/bin/env python3
"""Oxford Acute Severity of Illness Score (OASIS), first ICU day.

Point thresholds and precedence follow MIT-LCP's MIMIC-IV oasis.sql.
This is a research implementation, not a treatment or triage rule.
"""
import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

REQUIRED_FIELDS = (
    "age", "pre_icu_los_hours", "gcs_min", "heart_rate_min", "heart_rate_max",
    "map_min", "map_max", "respiratory_rate_min", "respiratory_rate_max",
    "temperature_min", "temperature_max", "urine_output_ml",
    "mechanically_ventilated", "elective_surgery",
)
BOOLEAN_FIELDS = ("mechanically_ventilated", "elective_surgery")
NUMERIC_FIELDS = tuple(k for k in REQUIRED_FIELDS if k not in BOOLEAN_FIELDS)


def _number(name, value):
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        raise ValueError(f"{name}: a finite number is required")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: a finite number is required") from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name}: must be finite and non-negative")
    return result


def _boolean(name, value):
    if isinstance(value, bool):
        return value
    if value is None:
        raise ValueError(f"{name}: yes or no is required")
    normalized = str(value).strip().lower()
    if normalized in ("yes", "true", "1"):
        return True
    if normalized in ("no", "false", "0"):
        return False
    raise ValueError(f"{name}: use yes/no, true/false or 1/0")


def calculate_metrics(**kwargs):
    """Calculate a complete OASIS score using first-24-hour observations.

    Minima and maxima are measured over the first ICU day. Do not substitute a
    single spot vital sign for both extrema unless that is all that was observed,
    and do not treat missing values as normal. No PHI is required or retained.
    """
    unknown = set(kwargs) - set(REQUIRED_FIELDS)
    if unknown:
        raise ValueError("Unknown OASIS fields: " + ", ".join(sorted(unknown)))
    values = {k: _number(k, kwargs.get(k)) for k in NUMERIC_FIELDS}
    values.update({k: _boolean(k, kwargs.get(k)) for k in BOOLEAN_FIELDS})
    v = values

    if not 18 <= v["age"] <= 120:
        raise ValueError("age: this implementation is for adults aged 18–120")
    if not v["gcs_min"].is_integer() or not 3 <= v["gcs_min"] <= 15:
        raise ValueError("gcs_min: expected integer from 3 through 15")
    for prefix in ("heart_rate", "map", "respiratory_rate", "temperature"):
        if v[f"{prefix}_min"] > v[f"{prefix}_max"]:
            raise ValueError(f"{prefix}: minimum exceeds maximum")

    preicu_minutes = v["pre_icu_los_hours"] * 60
    hr_min, hr_max = v["heart_rate_min"], v["heart_rate_max"]
    map_min, map_max = v["map_min"], v["map_max"]
    rr_min, rr_max = v["respiratory_rate_min"], v["respiratory_rate_max"]
    temp_min, temp_max = v["temperature_min"], v["temperature_max"]
    urine = v["urine_output_ml"]
    age = v["age"]
    gcs = int(v["gcs_min"])

    points = {
        "pre_icu_los": (5 if preicu_minutes < 10.2 else
                        3 if preicu_minutes < 297 else
                        0 if preicu_minutes < 1440 else
                        2 if preicu_minutes < 18708 else 1),
        "age": (0 if age < 24 else 3 if age <= 53 else
                6 if age <= 77 else 9 if age <= 89 else 7),
        "gcs": (10 if gcs <= 7 else 4 if gcs < 14 else 3 if gcs == 14 else 0),
        "heart_rate": (6 if hr_max > 125 else 4 if hr_min < 33 else
                       3 if hr_max >= 107 else 1 if hr_max >= 89 else 0),
        "map": (4 if map_min < 20.65 else 3 if map_min < 51 else
                3 if map_max > 143.44 else 2 if map_min < 61.33 else 0),
        "respiratory_rate": (10 if rr_min < 6 else 9 if rr_max > 44 else
                             6 if rr_max > 30 else 1 if rr_max > 22 else
                             1 if rr_min < 13 else 0),
        "temperature": (6 if temp_max > 39.88 else
                        4 if (33.22 <= temp_min <= 35.93 or
                              33.22 <= temp_max <= 35.93) else
                        3 if temp_min < 33.22 else
                        2 if 35.93 < temp_min <= 36.39 else
                        2 if 36.89 <= temp_max <= 39.88 else 0),
        "urine_output": (10 if urine < 671.09 else 8 if urine > 6896.80 else
                         5 if urine < 1427 else 1 if urine <= 2544.14 else 0),
        "mechanical_ventilation": (9 if v["mechanically_ventilated"] else 0),
        "elective_surgery": (0 if v["elective_surgery"] else 6),
    }
    score = sum(points.values())
    # Original published cohort calibration; not a validated individual decision rule.
    mortality = 100 / (1 + math.exp(-(-6.1746 + 0.1275 * score)))
    return {
        "tool": "oasis-icu-severity-score",
        "score": score,
        "component_scores": points,
        "estimated_in_hospital_mortality_percent": round(mortality, 2),
        "calibration_note": "Original OASIS cohort equation; local validation required.",
    }


def _validate_csv_path(path, must_exist=False):
    """Preserve absolute paths, but reject explicit parent traversal/null bytes."""
    path = os.fspath(path)
    if "\x00" in path:
        raise ValueError("Path contains null bytes")
    if ".." in Path(path).parts:
        raise ValueError(f"Path traversal detected in: {path}")
    normalized = os.path.normpath(path)
    if must_exist and not os.path.isfile(normalized):
        raise FileNotFoundError(f"Input file not found: {path}")
    return normalized


def _safe_csv_cell(value):
    """Prevent spreadsheet formula execution in exported identifier columns."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def process_batch(input_csv, output_csv):
    input_csv = _validate_csv_path(input_csv, must_exist=True)
    output_csv = _validate_csv_path(output_csv)
    if os.path.abspath(input_csv) == os.path.abspath(output_csv):
        raise ValueError("Output path must differ from input path")
    with open(input_csv, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate CSV column names")
        missing = set(REQUIRED_FIELDS) - set(fields)
        unknown = set(fields) - set(REQUIRED_FIELDS) - {"record_id"}
        if missing or unknown:
            raise ValueError(f"Invalid CSV header: missing={sorted(missing)} unknown={sorted(unknown)}")
        rows = []
        for number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"CSV row {number}: unexpected extra columns")
            try:
                result = calculate_metrics(**{k: row.get(k) for k in REQUIRED_FIELDS})
            except ValueError as exc:
                raise ValueError(f"CSV row {number}: {exc}") from exc
            out = {"record_id": _safe_csv_cell(row.get("record_id", ""))}
            out.update({key: row[key] for key in REQUIRED_FIELDS})
            out["score"] = result["score"]
            out["estimated_in_hospital_mortality_percent"] = result["estimated_in_hospital_mortality_percent"]
            out.update({f"points_{key}": value for key, value in result["component_scores"].items()})
            rows.append(out)
    cols = ["record_id", *REQUIRED_FIELDS, "score",
            "estimated_in_hospital_mortality_percent",
            *[f"points_{key}" for key in calculate_metrics(**{
                **{k: 1 for k in NUMERIC_FIELDS},
                "age": 18, "gcs_min": 15,
                "mechanically_ventilated": False, "elective_surgery": True,
            })["component_scores"]]]
    with open(output_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Processed {len(rows)} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="OASIS first-day ICU scoring (adult research use)")
    sub = parser.add_subparsers(dest="command", required=True)
    single = sub.add_parser("single", help="Score one complete first-day ICU observation")
    for field in NUMERIC_FIELDS:
        single.add_argument("--" + field.replace("_", "-"), type=float, required=True)
    for field in BOOLEAN_FIELDS:
        single.add_argument("--" + field.replace("_", "-"), required=True, help="yes or no")
    batch = sub.add_parser("batch", help="Score de-identified CSV observations")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            print(json.dumps(calculate_metrics(**{k: v for k, v in vars(args).items() if k != "command"}), indent=2))
        else:
            process_batch(args.input, args.output)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
