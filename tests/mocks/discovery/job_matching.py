from dataclasses import dataclass


@dataclass
class JobPreferences:
    target_roles: list[str]
    keywords: list[str]
    min_salary: int
    preferred_location: str
    preferred_contract_type: str
    preferred_remote_policy: str


class JobMatcher:
    def __init__(self, prefs: JobPreferences):
        self.prefs = prefs

    def match_job(self, job: dict) -> tuple[bool, float, str]:
        """Mock job matching logic."""
        return True, 90.0, "Mock match reasons"
