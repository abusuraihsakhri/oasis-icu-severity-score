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
    """Tests for core OASIS score calculation."""

    def test_basic_calculation(self):
        res = calculate_metrics(v1=10.0, v2=5.0, v3=2.0)
        assert res["score"] == 13.17  # 10 + 5/2 + 2/3 ≈ 13.17 rounded
        assert res["classification"] in ["Low / Standard", "Moderate / Intermediate", "High / Severe"]

    def test_empty_input(self):
        res = calculate_metrics()
        assert res["score"] > 0
        assert res["inputs_evaluated"] == 0

    def test_string_input_ignored(self):
        res = calculate_metrics(v1=10.0, name="patient-name")
        assert res["inputs_evaluated"] == 2

    def test_classification_thresholds(self):
        low = calculate_metrics(v1=5.0)
        assert low["classification"] == "Low / Standard"

        moderate = calculate_metrics(v1=15.0)
        assert moderate["classification"] == "Moderate / Intermediate"

        high = calculate_metrics(v1=30.0)
        assert high["classification"] == "High / Severe"


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
