"""CV Tailoring System for Job Scout.

This module provides AI-powered CV tailoring based on job requirements.
Generates personalized CVs by matching skills and experience to job descriptions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

class CVTailor:
    """AI-powered CV tailoring system."""
    
    def __init__(self, cv_path: Path, config: Optional[Dict] = None):
        """Initialize CV Tailor with base CV.
        
        Args:
            cv_path: Path to base CV (JSON/YAML format)
            config: Optional configuration for tailoring preferences
        """
        self.cv_path = Path(cv_path)
        self.config = config or {}
        self.base_cv = self._load_cv()
        
        # Initialize logger lazily to avoid circular imports
        self.logger = logger
        
    def _load_cv(self) -> Dict:
        """Load CV from file."""
        try:
            if self.cv_path.suffix.lower() == '.json':
                return json.loads(self.cv_path.read_text())
            elif self.cv_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                return yaml.safe_load(self.cv_path.read_text())
            else:
                raise ValueError(f"Unsupported CV format: {self.cv_path.suffix}")
        except Exception as e:
            self.logger.error(f"Failed to load CV: {e}")
            raise
    
    def _extract_keywords(self, job_description: str, skills_list: List[str]) -> Set[str]:
        """Extract matching keywords from job description."""
        job_desc_lower = job_description.lower()
        matched = {skill for skill in skills_list if skill.lower() in job_desc_lower}
        self.logger.debug(f"Extracted keywords: {matched}")
        return matched
    
    def _calculate_relevance(self, job_data: Dict) -> float:
        """Calculate relevance score between CV and job."""
        score = 0.0
        
        # Title match bonus (20%)
        job_title = job_data.get('title', '').lower()
        cv_titles = [exp.get('title', '').lower() for exp in self.base_cv.get('experience', [])]
        if any(title in job_title or job_title in title for title in cv_titles):
            score += 20.0
        
        # Skills match (50%)
        if 'description' in job_data:
            job_skills = self._extract_keywords(job_data['description'], self.base_cv.get('skills', []))
            score += min(len(job_skills) * 5, 50.0)
        
        # Experience level match (15%)
        # TODO: Parse years from job description and compare to CV
        
        # Location match (10%)
        if job_data.get('location', '').lower().find('uk') != -1 or job_data.get('remote_policy') in ['remote', 'hybrid']:
            score += 10.0
        
        # Salary match (5%)
        # TODO: Compare salary preferences
        
        return min(score, 100.0)
    
    def tailor_cv(self, job_data: Dict) -> Dict:
        """Tailor CV for specific job based on relevance."""
        relevance = self._calculate_relevance(job_data)
        self.logger.info(f"Job relevance score: {relevance:.1f}%")
        
        if relevance < 30:
            self.logger.warning(f"Low relevance job: {job_data.get('title')}")
        
        # Create tailored CV
        tailored = {
            'metadata': {
                'original_cv': str(self.cv_path),
                'target_job': job_data.get('title'),
                'target_company': job_data.get('company'),
                'relevance_score': round(relevance, 1),
                'tailored_date': '2024-01-01',  # Placeholder - should use actual date
                'uk_focus': job_data.get('location', '').lower().find('uk') != -1 or 'uk' in str(job_data.get('remote_policy', '')).lower()
            },
            'personal_info': self.base_cv.get('personal_info', {}),
            'summary': self._generate_summary(job_data, relevance),
            'skills': self._prioritize_skills(job_data),
            'experience': self._filter_experience(job_data, relevance),
            'education': self.base_cv.get('education', []),
            'certifications': self._filter_certifications(job_data),
        }
        
        return tailored
    
    def _generate_summary(self, job_data: Dict, relevance: float) -> str:
        """Generate personalized summary for job."""
        job_title = job_data.get('title', 'the position')
        company = job_data.get('company', 'your company')
        
        summary_parts = []
        summary_parts.append(
            f"I am writing to express my strong interest in the {job_title} position at {company}. "
        )
        
        # Add achievement context
        if relevance > 70:
            summary_parts.append(
                "With my extensive experience and demonstrated expertise, I am confident "
                "in my ability to deliver significant value to your team."
            )
        elif relevance > 50:
            summary_parts.append(
                "My background aligns well with this role, particularly regarding key technical requirements."
            )
        else:
            summary_parts.append(
                "I am excited about the opportunity to apply my skills and grow professionally "
                "in this challenging role."
            )
        
        return ' '.join(summary_parts)
    
    def _prioritize_skills(self, job_data: Dict) -> List[Dict]:
        """Prioritize skills that match job requirements."""
        description = job_data.get('description', '').lower()
        all_skills = self.base_cv.get('skills', [])
        
        prioritized = []
        for skill in all_skills:
            skill_lower = skill.get('name', '').lower()
            if skill_lower in description:
                prioritized.append({**skill, 'priority': 'high'})
            else:
                prioritized.append({**skill, 'priority': 'standard'})
        
        # Sort by priority
        prioritized.sort(key=lambda x: x['priority'] == 'high', reverse=True)
        return prioritized
    
    def _filter_experience(self, job_data: Dict, relevance: float) -> List[Dict]:
        """Filter experience to highlight most relevant roles."""
        experience = self.base_cv.get('experience', [])
        if not experience:
            return []
        
        # For high relevance jobs, show all experience
        if relevance > 70:
            return experience
        
        # For medium relevance, show most recent first
        if relevance > 50:
            # Sort by date (assume 'date' field exists in format YYYY-MM or similar)
            return sorted(experience[:3], key=lambda x: x.get('date', ''), reverse=True)
        
        # For low relevance, show only most recent
        return [experience[0]] if experience else []
    
    def _filter_certifications(self, job_data: Dict) -> List[str]:
        """Filter certifications relevant to job."""
        all_certs = self.base_cv.get('certifications', [])
        description = job_data.get('description', '').lower()
        
        relevant_certs = []
        for cert in all_certs:
            cert_lower = str(cert).lower()
            # Simple heuristic: if cert name appears in job description, include it
            if any(word in description for word in cert_lower.split() if len(word) > 3):
                relevant_certs.append(cert)
        
        return relevant_certs
    
    def save_tailored_cv(self, tailored_cv: Dict, output_path: Path) -> Path:
        """Save tailored CV to file."""
        output_path = Path(output_path)
        
        try:
            # Determine format based on extension
            if output_path.suffix.lower() == '.json':
                output_path.write_text(json.dumps(tailored_cv, indent=2))
            elif output_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                output_path.write_text(yaml.dump(tailored_cv, default_flow_style=False))
            elif output_path.suffix.lower() == '.md':
                output_path.write_text(self._to_markdown(tailored_cv))
            else:
                # Default to JSON
                output_path = output_path.parent / (output_path.stem + '.json')
                output_path.write_text(json.dumps(tailored_cv, indent=2))
            
            self.logger.info(f"Tailored CV saved: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to save tailored CV: {e}")
            raise
    
    def _to_markdown(self, cv: Dict) -> str:
        """Convert CV to markdown format."""
        lines = []
        
        # Header
        personal = cv.get('personal_info', {})
        lines.append(f"# {personal.get('name', 'CV')}")
        lines.append(f"{personal.get('email', '')} | {personal.get('phone', '')}")
        lines.append(f"{personal.get('linkedin', '').replace('https://linkedin.com/', '')}")
        lines.append("")
        
        # Summary
        lines.append(f"## Summary\n{cv.get('summary', 'No summary provided.')}")
        lines.append("")
        
        # Skills
        lines.append("## Skills")
        for skill in cv.get('skills', []):
            priority_emoji = "🟢" if skill.get('priority') == 'high' else "⚪"
            lines.append(f"- {priority_emoji} {skill.get('name', '')}: {skill.get('level', 'experienced')}")
        lines.append("")
        
        # Experience
        lines.append("## Experience")
        for exp in cv.get('experience', []):
            title = exp.get('title', 'Position')
            company = exp.get('company', 'Company')
            date = exp.get('date', 'Date range')
            location = exp.get('location', '')
            lines.append(f"### {title}")
            lines.append(f"**{company}** | {date} {location}")
            for item in exp.get('achievements', []):
                lines.append(f"- {item}")
            lines.append("")
        
        # Education
        lines.append("## Education")
        for edu in cv.get('education', []):
            degree = edu.get('degree', 'Degree')
            school = edu.get('school', 'School')
            year = edu.get('year', '')
            lines.append(f"- {degree}, {school} {year}")
        lines.append("")
        
        # Tailoring metadata
        meta = cv.get('metadata', {})
        lines.append(f"*Tailored for {meta.get('target_job', 'this role')} at {meta.get('target_company', 'the company')}: {meta.get('relevance_score', 0)}% match*")
        
        return "\n".join(lines)

    def generate_cv_for_job(self, job_data: Dict, output_path: Path = None) -> Path:
        """Complete pipeline: tailor CV and save to file."""
        tailored_cv = self.tailor_cv(job_data)
        
        if output_path:
            return self.save_tailored_cv(tailored_cv, output_path)
        else:
            # Auto-generate filename
            company = job_data.get('company', 'unknown').replace(' ', '_')
            job_title = job_data.get('title', 'job').replace(' ', '_')[:30]
            safe_path = Path(f"tailored_cvs/tailored_{company}_{job_title}.md")
            safe_path.parent.mkdir(exist_ok=True)
            return self.save_tailored_cv(tailored_cv, safe_path)