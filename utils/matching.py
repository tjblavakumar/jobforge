"""
Matching module for JobForge.
Scores jobs based on user profile using embeddings and optional OpenAI.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    from .openai_integration import get_analyzer
    HAS_OPENAI_INTEGRATION = True
except ImportError:
    HAS_OPENAI_INTEGRATION = False


class JobMatcher:
    """Score and rank jobs based on user profile"""
    
    def __init__(self, use_openai: bool = False, api_key: Optional[str] = None):
        self.use_openai = use_openai
        self.api_key = api_key
        self.model = None
        
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            except Exception as e:
                print(f"Warning: Could not load embeddings model: {e}")
    
    def score_job(self, job: Dict, user_profile: Dict) -> Tuple[float, Dict]:
        """
        Score a job (0-100) based on user profile.
        Returns (score, breakdown).
        """
        scores = {
            "semantic_match": 0,
            "salary_match": 0,
            "remote_bonus": 0,
            "skills_bonus": 0,
            "openai_score": 0
        }
        
        # 1. Semantic matching - JD vs profile
        if self.model and user_profile.get("summary"):
            semantic_score = self._semantic_similarity(
                job.get("jd_text", ""),
                user_profile.get("summary", "")
            ) * 100
            scores["semantic_match"] = semantic_score
        else:
            scores["semantic_match"] = 50  # Neutral
        
        # 2. Salary matching
        salary_score = self._salary_match(
            job.get("salary_min"),
            job.get("salary_max"),
            user_profile.get("expected_salary_min", 100000),
            user_profile.get("expected_salary_max", 250000)
        )
        scores["salary_match"] = salary_score
        
        # 3. Remote bonus
        if user_profile.get("prefer_remote") and job.get("is_remote"):
            scores["remote_bonus"] = 10
        elif not user_profile.get("prefer_remote") and not job.get("is_remote"):
            scores["remote_bonus"] = 5
        
        # 4. Skills bonus
        skills_bonus = self._skills_match(
            job.get("jd_text", "").lower(),
            user_profile.get("skills", [])
        )
        scores["skills_bonus"] = skills_bonus
        
        # 5. OpenAI deeper analysis
        if self.use_openai and self.api_key:
            scores["openai_score"] = self._openai_score(job, user_profile)
        
        # Calculate final score (weighted)
        final_score = (
            scores["semantic_match"] * 0.35 +
            scores["salary_match"] * 0.25 +
            scores["skills_bonus"] * 0.25 +
            scores["remote_bonus"] * 0.10 +
            scores["openai_score"] * 0.05
        )
        
        return max(0, min(100, final_score)), scores
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts (0-1)"""
        if not self.model or not text1 or not text2:
            return 0.5
        
        try:
            # Get embeddings
            emb1 = self.model.encode(text1[:512])  # Limit to 512 tokens
            emb2 = self.model.encode(text2[:512])
            
            # Cosine similarity
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return float(similarity)
        except Exception as e:
            print(f"Embedding error: {e}")
            return 0.5
    
    def _salary_match(self, job_min: int, job_max: int, 
                     user_min: int, user_max: int) -> float:
        """Score salary match (0-100)"""
        if not job_min or not job_max:
            return 50  # Neutral
        
        job_mid = (job_min + job_max) / 2
        user_mid = (user_min + user_max) / 2
        
        # Perfect match at user_mid
        difference = abs(job_mid - user_mid)
        score = max(0, 100 - (difference / user_mid) * 100)
        
        return min(100, score)
    
    def _skills_match(self, jd_text: str, user_skills: List[str]) -> float:
        """Score based on skills overlap (0-100)"""
        if not user_skills:
            return 50
        
        matches = 0
        for skill in user_skills:
            if skill.lower() in jd_text.lower():
                matches += 1
        
        # Bonus for multiple skill matches
        score = (matches / len(user_skills)) * 100
        
        # Cap at 100, add bonus if all skills present
        if matches == len(user_skills):
            score = min(100, score + 10)
        
        return min(100, score)
    
    def _openai_score(self, job: Dict, user_profile: Dict) -> float:
        """
        Get deeper job match score from OpenAI (Phase 1).
        Uses GPT-4o-mini for intelligent analysis if API key available.
        """
        if not self.use_openai or not self.api_key or not HAS_OPENAI_INTEGRATION:
            return 0.0
        
        try:
            analyzer = get_analyzer(self.api_key)
            if not analyzer or not analyzer.client:
                return 0.0
            
            # Get OpenAI analysis
            score, reasoning = analyzer.score_job_match(job, user_profile)
            # Normalize to 0-100 range
            return min(100, max(0, score))
        except Exception as e:
            print(f"OpenAI scoring error: {e}")
            return 0.0
    
    def rank_jobs(self, jobs: List[Dict], user_profile: Dict, 
                  filters: Optional[Dict] = None) -> List[Dict]:
        """
        Rank and filter jobs.
        
        filters: {
            "min_salary": int,
            "max_salary": int,
            "remote_only": bool,
            "companies": List[str],
            "min_match_score": float (0-100),
            "days_old": int
        }
        """
        from datetime import datetime, timedelta
        
        if not filters:
            filters = {}
        
        scored_jobs = []
        
        for job in jobs:
            # Apply hard filters
            if filters.get("min_salary") and job.get("salary_max", 0) < filters["min_salary"]:
                continue
            
            if filters.get("max_salary") and job.get("salary_min", 999999) > filters["max_salary"]:
                continue
            
            if filters.get("remote_only") and not job.get("is_remote"):
                continue
            
            if filters.get("companies") and job.get("company") not in filters["companies"]:
                continue
            
            if filters.get("days_old"):
                posted = job.get("posted_date")
                if posted and (datetime.now(timezone.utc) - posted) > timedelta(days=filters["days_old"]):
                    continue
            
            # Score the job
            score, breakdown = self.score_job(job, user_profile)
            
            if score >= filters.get("min_match_score", 0):
                job_with_score = job.copy()
                job_with_score["match_score"] = score
                job_with_score["score_breakdown"] = breakdown
                scored_jobs.append(job_with_score)
        
        # Sort by match score descending
        scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
        
        return scored_jobs


class SimpleJobMatcher:
    """Fallback matcher without ML dependencies"""
    
    def score_job_simple(self, job: Dict, user_profile: Dict) -> Tuple[float, Dict]:
        """Simple keyword-based scoring"""
        score = 50  # Base score
        
        # Salary bonus
        salary_min = job.get("salary_min", 0)
        salary_max = job.get("salary_max", 999999)
        user_min = user_profile.get("expected_salary_min", 100000)
        if salary_min <= user_min <= salary_max:
            score += 15
        
        # Remote bonus
        if user_profile.get("prefer_remote") and job.get("is_remote"):
            score += 15
        
        # Skills bonus
        jd_lower = job.get("jd_text", "").lower()
        skills = user_profile.get("skills", [])
        skill_matches = sum(1 for skill in skills if skill.lower() in jd_lower)
        score += min(20, skill_matches * 3)
        
        return min(100, score), {"manual_score": score}


# Global matchers
matchers = {}
simple_matcher = SimpleJobMatcher()


def get_matcher(use_openai: bool = False, api_key: Optional[str] = None) -> JobMatcher:
    """Get or create matcher instance"""
    global matchers
    cache_key = (bool(use_openai), bool(api_key))
    if cache_key not in matchers:
        matchers[cache_key] = JobMatcher(use_openai=use_openai, api_key=api_key)
    return matchers[cache_key]


if __name__ == "__main__":
    # Demo
    matcher = JobMatcher()
    
    sample_job = {
        "title": "Senior Python Engineer",
        "company": "Google",
        "jd_text": "We need a senior engineer experienced in Python, distributed systems, and cloud architecture."
    }
    
    sample_profile = {
        "summary": "5 years backend engineer, Python specialist, AWS certified",
        "skills": ["Python", "AWS", "Kubernetes"],
        "expected_salary_min": 150000,
        "expected_salary_max": 250000
    }
    
    score, breakdown = matcher.score_job(sample_job, sample_profile)
    print(f"Score: {score:.1f}/100")
    print(f"Breakdown: {json.dumps(breakdown, indent=2)}")
