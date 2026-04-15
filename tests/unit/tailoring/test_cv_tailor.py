"""Tests for CV tailoring module."""

from pathlib import Path

from src.tailoring.cv_tailor import tailor_cv


class TestTailorCV:
    """Test tailor_cv function."""

    def test_tailor_cv_without_output_path(self) -> None:
        """Test tailor_cv returns None when no output path provided."""
        base_cv = {"name": "John Doe", "experience": "5 years"}
        job_desc = "Python developer role"

        result = tailor_cv(base_cv, job_desc)
        assert result is None

    def test_tailor_cv_with_output_path(self, tmp_path: Path) -> None:
        """Test tailor_cv saves to file when output path provided."""
        base_cv = {"name": "Jane Smith", "skills": ["Python", "Django"]}
        job_desc = "Backend Developer"

        output_file = tmp_path / "tailored_cv.yaml"
        result = tailor_cv(base_cv, job_desc, output_file)

        assert result == output_file
        assert output_file.exists()

    def test_tailor_cv_preserves_base_cv(self, tmp_path: Path) -> None:
        """Test tailor_cv preserves original CV fields."""
        base_cv = {
            "name": "Alice",
            "email": "alice@example.com",
            "experience": "10 years",
            "skills": ["Java", "Spring"],
        }
        job_desc = "Java Developer"

        output_file = tmp_path / "cv.yaml"
        tailor_cv(base_cv, job_desc, output_file)

        content = output_file.read_text()
        assert "Alice" in content
        assert "alice@example.com" in content
        assert "Java" in content
        assert "Java Developer" in content

    def test_tailor_cv_adds_tailored_field(self, tmp_path: Path) -> None:
        """Test tailor_cv adds tailored_for field."""
        base_cv = {"name": "Bob"}
        job_desc = "DevOps Engineer"

        output_file = tmp_path / "cv.yaml"
        result = tailor_cv(base_cv, job_desc, output_file)

        assert result is not None
        assert "DevOps Engineer" in result.read_text()
