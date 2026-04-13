from typing import Optional, Dict, Any
from pathlib import Path
import yaml


def tailor_cv(
    base_cv: Dict[str, Any], job_description: str, output_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Tailor a CV to a job description.

    Args:
        base_cv: The base CV as a dictionary.
        job_description: The job description to tailor the CV to.
        output_path: Optional path to save the tailored CV.

    Returns:
        The path where the tailored CV was saved, or None if not saved.
    """
    tailored_cv = {
        **base_cv,
        "tailored_for": job_description,
    }

    if output_path:
        with open(output_path, "w") as f:
            yaml.dump(tailored_cv, f)
        return output_path
    return None
