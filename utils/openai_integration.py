"""
OpenAI Integration Module for JobForge Phase 1.
Provides GPT-4o-mini powered job analysis and matching.
"""

import json
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

try:
    from openai import OpenAI, RateLimitError, APIError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class OpenAIJobAnalyzer:
    """Analyze jobs and profiles using OpenAI's GPT-4o-mini"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key"""
        self.api_key = api_key
        self.client = None
        self.model = "gpt-4o-mini"  # Fast, affordable, good quality
        
        if api_key and HAS_OPENAI:
            try:
                self.client = OpenAI(api_key=api_key)
                self._test_connection()
            except Exception as e:
                print(f"OpenAI initialization error: {e}")
                self.client = None
    
    def _test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = self.client.models.list()
            return bool(response)
        except Exception as e:
            print(f"OpenAI connection test failed: {e}")
            return False
    
    def score_job_match(self, job: Dict, profile: Dict) -> Tuple[float, str]:
        """
        Use GPT-4o-mini to score how well a job matches a profile.
        Returns (score 0-100, reasoning).
        """
        if not self.client:
            return 0.0, "OpenAI not configured"
        
        try:
            prompt = self._build_match_prompt(job, profile)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert career advisor analyzing job fit for a software engineer."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                score = float(result.get("score", 0))
                reasoning = result.get("reasoning", "")
                return max(0, min(100, score)), reasoning
            except json.JSONDecodeError:
                # Fallback parsing
                lines = result_text.split('\n')
                for line in lines:
                    if 'score' in line.lower():
                        try:
                            score = float(''.join(filter(str.isdigit, line.split(':')[1])))
                            return max(0, min(100, score)), result_text[:100]
                        except:
                            pass
                return 50.0, result_text[:100]
        
        except RateLimitError:
            return 0.0, "Rate limited - try again later"
        except APIError as e:
            return 0.0, f"API error: {str(e)[:50]}"
        except Exception as e:
            return 0.0, f"Error: {str(e)[:50]}"
    
    def _build_match_prompt(self, job: Dict, profile: Dict) -> str:
        """Build prompt for job matching analysis"""
        return f"""
Analyze how well this job matches this candidate's profile.

CANDIDATE PROFILE:
- Title: {profile.get('title', 'N/A')}
- Experience: {profile.get('years_exp', 0)} years
- Skills: {', '.join(profile.get('skills', [])[:10])}
- Summary: {profile.get('summary', 'N/A')[:200]}

JOB DETAILS:
- Title: {job.get('title', 'N/A')}
- Company: {job.get('company', 'N/A')}
- Location: {job.get('location', 'N/A')} (Remote: {job.get('is_remote', False)})
- Salary: ${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}
- Description (first 300 chars): {job.get('jd_text', 'N/A')[:300]}

Return ONLY valid JSON with this exact format (no markdown):
{{"score": <0-100>, "reasoning": "<brief analysis>"}}

Consider:
1. Skill alignment (exact matches are best)
2. Experience level match
3. Growth opportunity
4. Salary expectations
5. Location preference
"""
    
    def generate_interview_prep(self, job: Dict) -> str:
        """Generate interview prep questions for a job"""
        if not self.client:
            return "OpenAI not configured"
        
        try:
            prompt = f"""
Based on this job description, generate 5 key interview questions a candidate should prepare for.

JOB: {job.get('title', 'Software Engineer')} at {job.get('company', 'Tech Company')}
DESCRIPTION: {job.get('jd_text', 'N/A')[:500]}

Return as numbered list with brief answers. Be concise and practical.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error generating prep: {str(e)}"
    
    def tailor_resume_for_job(self, profile: Dict, job: Dict) -> str:
        """Generate resume tailoring suggestions for a specific job"""
        if not self.client:
            return "OpenAI not configured"
        
        try:
            prompt = f"""
Suggest how to tailor a resume for this specific job. Keep it concise and actionable.

CANDIDATE: {profile.get('summary', 'N/A')[:200]}
JOB: {job.get('title')} at {job.get('company')}
KEY REQUIREMENTS: {job.get('jd_text', 'N/A')[:300]}

Return 3-5 specific resume bullet points this candidate should highlight.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error tailoring resume: {str(e)}"
    
    def salary_negotiation_tips(self, job: Dict, profile: Dict) -> str:
        """Generate salary negotiation tips based on market data and candidate profile"""
        if not self.client:
            return "OpenAI not configured"
        
        try:
            salary_range = f"${job.get('salary_min', 0):,} - ${job.get('salary_max', 0):,}"
            prompt = f"""
Give brief salary negotiation tips for this role.

ROLE: {job.get('title')} at {job.get('company')}
LOCATION: {job.get('location', 'Remote')}
POSTED SALARY: {salary_range}
CANDIDATE: {profile.get('years_exp', 0)} years experience, {profile.get('title', 'Engineer')}

Return 2-3 practical negotiation tips. Be realistic and data-driven for the market.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=250
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error generating tips: {str(e)}"


# Global analyzer instance
analyzer = None


def get_analyzer(api_key: Optional[str] = None) -> Optional[OpenAIJobAnalyzer]:
    """Get or create global analyzer instance"""
    global analyzer
    if analyzer is None and api_key:
        analyzer = OpenAIJobAnalyzer(api_key)
    return analyzer


def validate_api_key(api_key: str) -> bool:
    """Validate OpenAI API key by attempting a test call"""
    if not api_key or not HAS_OPENAI:
        return False
    
    try:
        test_analyzer = OpenAIJobAnalyzer(api_key)
        return test_analyzer.client is not None
    except Exception as e:
        print(f"Key validation error: {e}")
        return False


if __name__ == "__main__":
    # Demo
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        analyzer = OpenAIJobAnalyzer(api_key)
        
        sample_job = {
            "title": "Senior Python Engineer",
            "company": "Google",
            "jd_text": "We need Python experts with 7+ years distributed systems experience.",
            "location": "Mountain View, CA",
            "salary_min": 200000,
            "salary_max": 280000,
            "is_remote": False
        }
        
        sample_profile = {
            "title": "Backend Engineer",
            "years_exp": 8,
            "skills": ["Python", "Go", "Kubernetes", "AWS"],
            "summary": "8 years building distributed systems at scale"
        }
        
        score, reasoning = analyzer.score_job_match(sample_job, sample_profile)
        print(f"Match Score: {score:.1f}%")
        print(f"Reasoning: {reasoning}")
    else:
        print("Set OPENAI_API_KEY environment variable to test")
