"""CV Tailoring Module for Job Scout.

Generates tailored CVs and cover letters based on job requirements.
"""

from .cv_tailor import CVTailor
from .cover_letter_generator import CoverLetterGenerator

__all__ = ["CVTailor", "CoverLetterGenerator"]