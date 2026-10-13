"""
Focused tests for security hardening and input validation.
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import AuditTrail, PHIGuard, SecurityException
from oasis_score import _validate_csv_path, calculate_metrics


class TestAuditTrailSecurity:
    """Tests for HMAC audit trail security requirements."""

    def test_audit_trail_rejects_missing_secret_key(self, monkeypatch):
        """AuditTrail must not initialize with a hardcoded default secret."""
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY must be provided"):
            AuditTrail()

    def test_audit_trail_rejects_short_secret_key(self):
        """AuditTrail must enforce minimum key entropy."""
        with pytest.raises(ValueError, match="at least 16 characters"):
            AuditTrail(secret_key="short")

    def test_audit_trail_accepts_valid_key(self, monkeypatch):
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        trail = AuditTrail(secret_key="a" * 32)
        assert trail.logs == []

    def test_audit_trail_accepts_env_var(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "env-based-secret-key-1234567890")
        trail = AuditTrail()
        assert trail.logs == []


class TestCsvPathValidation:
    """Tests for CSV path traversal protection."""

    def test_rejects_null_bytes(self):
        with pytest.raises(ValueError, match="null bytes"):
            _validate_csv_path("file\x00name.csv")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_csv_path("../../etc/passwd")

    def test_rejects_missing_input_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _validate_csv_path(str(tmp_path / "nonexistent.csv"), must_exist=True)

    def test_accepts_valid_path(self, tmp_path):
        csv_file = tmp_path / "valid.csv"
        csv_file.write_text("a,b\n1,2\n")
        result = _validate_csv_path(str(csv_file), must_exist=True)
        assert result.endswith("valid.csv")


class TestCalculateMetrics:
    @staticmethod
    def normal(**overrides):
        values = dict(age=40, pre_icu_los_hours=8, gcs_min=15,
                      heart_rate_min=70, heart_rate_max=88,
                      map_min=80, map_max=90, respiratory_rate_min=16,
                      respiratory_rate_max=20, temperature_min=36.4,
                      temperature_max=36.8, urine_output_ml=3000,
                      mechanically_ventilated=False, elective_surgery=True)
        values.update(overrides)
        return values

    def test_published_component_scores(self):
        result = calculate_metrics(**self.normal())
        assert result["component_scores"]["age"] == 3
        assert result["component_scores"]["pre_icu_los"] == 0
        assert result["score"] == 3

    def test_high_abnormal_case(self):
        result = calculate_metrics(**self.normal(
            age=80, pre_icu_los_hours=0, gcs_min=3,
            heart_rate_min=20, heart_rate_max=140,
            map_min=10, map_max=160, respiratory_rate_min=2,
            respiratory_rate_max=50, temperature_min=32,
            temperature_max=41, urine_output_ml=100,
            mechanically_ventilated=True, elective_surgery=False))
        assert result["score"] == 71  # 5+9+10+6+4+10+6+10+9+6

    @pytest.mark.parametrize("changes", [
        {"age": None}, {"heart_rate_max": float("nan")},
        {"map_min": float("inf")}, {"gcs_min": 2},
        {"gcs_min": 14.5}, {"temperature_min": 38, "temperature_max": 37},
        {"mechanically_ventilated": "maybe"},
    ])
    def test_invalid_inputs_rejected(self, changes):
        with pytest.raises(ValueError):
            calculate_metrics(**self.normal(**changes))

    def test_unknown_and_missing_inputs_rejected(self):
        with pytest.raises(ValueError, match="Unknown"):
            calculate_metrics(**self.normal(v1=99))
        with pytest.raises(ValueError):
            calculate_metrics()

    def test_hmac_detects_modified_record(self):
        trail = AuditTrail(secret_key="k" * 32)
        trail.log("test", "test", "create", {"status": "OK"})
        assert trail.verify_integrity()
        trail.logs[0]["actor"] = "intruder"
        assert not trail.verify_integrity()

    def test_audit_get_trail_is_defensive_copy(self):
        trail = AuditTrail(secret_key="k" * 32)
        trail.log("test", "test", "create", {"status": "OK"})
        trail.get_trail()[0]["event_type"] = "changed"
        assert trail.verify_integrity()


class TestEnrichmentEngineValidation:
    """Tests for enrichment engine input validation."""

    def test_rejects_negative_threshold(self):
        from enrichment import BaseEnrichmentEngine
        with pytest.raises(ValueError, match="threshold must be positive"):
            BaseEnrichmentEngine(threshold=-1.0)

    def test_rejects_zero_threshold(self):
        from enrichment import BaseEnrichmentEngine
        with pytest.raises(ValueError, match="threshold must be positive"):
            BaseEnrichmentEngine(threshold=0.0)
