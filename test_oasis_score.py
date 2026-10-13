import csv
import pytest
from oasis_score import calculate_metrics, process_batch, REQUIRED_FIELDS


def observation(**extra):
    fields = dict(
        age=40, pre_icu_los_hours=8, gcs_min=15,
        heart_rate_min=70, heart_rate_max=88, map_min=80, map_max=90,
        respiratory_rate_min=16, respiratory_rate_max=20,
        temperature_min=36.4, temperature_max=36.8, urine_output_ml=3000,
        mechanically_ventilated=False, elective_surgery=True,
    )
    fields.update(extra)
    return fields


def test_oasis_single_reference_bins():
    result = calculate_metrics(**observation())
    assert result["score"] == 3
    assert result["component_scores"]["elective_surgery"] == 0
    assert result["estimated_in_hospital_mortality_percent"] > 0


def test_oasis_boundary_pre_icu_minutes():
    assert calculate_metrics(**observation(pre_icu_los_hours=10.19/60))["component_scores"]["pre_icu_los"] == 5
    assert calculate_metrics(**observation(pre_icu_los_hours=10.2/60))["component_scores"]["pre_icu_los"] == 3


def test_oasis_single_vital_extreme_precedence():
    points = calculate_metrics(**observation(
        heart_rate_min=20, heart_rate_max=130, respiratory_rate_min=2,
        respiratory_rate_max=50))["component_scores"]
    assert points["heart_rate"] == 6
    assert points["respiratory_rate"] == 10


def test_oasis_batch(tmp_path):
    inp = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    fields = ["record_id", *REQUIRED_FIELDS]
    with inp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"record_id": "=2+2", **observation()})
    process_batch(inp, out)
    with out.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["score"] == "3"
    assert row["record_id"] == "'=2+2"
    with pytest.raises(ValueError, match="Output path"):
        process_batch(inp, inp)


def test_batch_rejects_obsolete_columns(tmp_path):
    inp = tmp_path / "legacy.csv"
    inp.write_text("Patient_ID,v1,v2,v3\nPT-001,10,5,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid CSV header"):
        process_batch(inp, tmp_path / "out.csv")
