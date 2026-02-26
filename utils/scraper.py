"""
Scraper module for JobForge.
Mock scraper for Phase 0 - returns realistic demo job data.
Phase 1 will implement real Playwright + stealth scraping.
"""

import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import json


class MockScraper:
    """Mock scraper that returns realistic demo data"""
    
    def __init__(self):
        self.demo_jobs_templates = [
            {
                "titles": ["Senior Software Engineer", "Software Engineer III", "Principal Engineer"],
                "skills": ["Python", "Java", "Go", "C++", "System Design", "Distributed Systems"],
                "salary_min": 160000,
                "salary_max": 280000
            },
            {
                "titles": ["Machine Learning Engineer", "ML Engineer", "AI Engineer"],
                "skills": ["Python", "PyTorch", "TensorFlow", "CUDA", "Computer Vision", "NLP"],
                "salary_min": 170000,
                "salary_max": 300000
            },
            {
                "titles": ["Frontend Engineer", "React Engineer", "Web Engineer"],
                "skills": ["React", "TypeScript", "JavaScript", "CSS", "WebGL", "Performance"],
                "salary_min": 150000,
                "salary_max": 260000
            },
            {
                "titles": ["Backend Engineer", "Server Engineer", "API Engineer"],
                "skills": ["Node.js", "Python", "Java", "PostgreSQL", "Redis", "Microservices"],
                "salary_min": 155000,
                "salary_max": 265000
            },
            {
                "titles": ["DevOps Engineer", "Cloud Engineer", "Infrastructure Engineer"],
                "skills": ["Kubernetes", "AWS", "Azure", "Terraform", "Go", "Linux"],
                "salary_min": 160000,
                "salary_max": 270000
            },
            {
                "titles": ["Data Engineer", "Analytics Engineer", "Data Platform Engineer"],
                "skills": ["SQL", "Spark", "Python", "Airflow", "BigQuery", "Data Modeling"],
                "salary_min": 155000,
                "salary_max": 265000
            },
            {
                "titles": ["Security Engineer", "Application Security Engineer", "Security Researcher"],
                "skills": ["Cryptography", "Python", "C", "Rust", "Vulnerability Assessment"],
                "salary_min": 165000,
                "salary_max": 280000
            },
            {
                "titles": ["Product Manager", "Senior PM", "Technical PM"],
                "skills": ["Product Strategy", "Analytics", "User Research", "SQL", "Roadmapping"],
                "salary_min": 140000,
                "salary_max": 240000
            }
        ]
        
        self.locations = ["San Francisco, CA", "Mountain View, CA", "Seattle, WA", "Austin, TX", 
                         "New York, NY", "Boston, MA", "Remote", "Los Angeles, CA"]
        
        self.job_descriptions = [
            "Join our world-class team working on {tech} at scale. We're hiring {role} to help us solve challenging problems.",
            "We are looking for a talented {role} with strong {tech} background to join our {team} team.",
            "Are you interested in {tech}? We're seeking {role} engineers to build the next generation of products.",
            "Help us scale infrastructure serving {scale} users. {role} position open.",
            "{role} needed to work on core systems using {tech}. Work on impactful projects."
        ]
    
    async def scrape_company(self, company_name: str, careers_url: str, limit: int = 3) -> List[Dict]:
        """Mock scrape company careers page"""
        company_name_lc = company_name.lower()
        careers_url_lc = careers_url.lower()
        if (
            "california state jobs" in company_name_lc
            or "calcareers" in company_name_lc
            or "calcareers" in careers_url_lc
            or "ca.gov" in careers_url_lc
        ):
            return await self.scrape_california_state_jobs(careers_url, limit)

        # Simulate network delay
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        jobs = []
        safe_limit = max(1, limit)
        num_jobs = random.randint(1, safe_limit)
        
        for i in range(num_jobs):
            template = random.choice(self.demo_jobs_templates)
            is_remote = random.choice([True, False, False])  # 33% remote
            
            job = {
                "title": random.choice(template["titles"]),
                "company": company_name,
                "location": "Remote" if is_remote else random.choice(self.locations),
                "salary_min": template["salary_min"] + random.randint(-10000, 20000),
                "salary_max": template["salary_max"] + random.randint(-10000, 30000),
                "is_remote": is_remote,
                "link": f"{careers_url.rstrip('/')}/job-{i+1}",
                "jd_text": self._generate_job_description(random.choice(template["titles"]), 
                                                          random.sample(template["skills"], 3),
                                                          company_name),
                "posted_date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
                "source": company_name
            }
            jobs.append(job)
        
        return jobs

    async def scrape_california_state_jobs(self, careers_url: str, limit: int = 3) -> List[Dict]:
        """Mock scrape California state jobs (CalCareers)"""
        await asyncio.sleep(random.uniform(0.4, 1.2))

        roles = [
            "Information Technology Specialist I",
            "Information Technology Specialist II",
            "Systems Software Specialist",
            "Data Analyst",
            "Program Analyst",
            "Cybersecurity Analyst"
        ]
        ca_locations = [
            "Sacramento, CA",
            "Los Angeles, CA",
            "San Diego, CA",
            "Oakland, CA",
            "Fresno, CA"
        ]

        jobs = []
        safe_limit = max(1, limit)
        num_jobs = random.randint(1, safe_limit)

        for i in range(num_jobs):
            title = random.choice(roles)
            salary_min = random.randint(85000, 135000)
            salary_max = salary_min + random.randint(15000, 40000)
            location = random.choice(ca_locations)

            jobs.append({
                "title": title,
                "company": "California State Jobs",
                "location": location,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "is_remote": False,
                "link": f"{careers_url.rstrip('/')}/job-{i+1}",
                "jd_text": (
                    f"Join the State of California as a {title}. "
                    "Help deliver public services through secure, reliable technology systems.\n\n"
                    "Requirements:\n"
                    "- Experience with public-sector or enterprise systems\n"
                    "- Strong collaboration and communication skills\n"
                    "- Knowledge of policy, compliance, and service delivery\n"
                ),
                "posted_date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 20)),
                "source": "California State Jobs"
            })

        return jobs
    
    async def scrape_multiple_companies(self, companies: List[Dict], limit: int = 2) -> List[Dict]:
        """Mock scrape multiple companies"""
        all_jobs = []
        
        for company in companies:
            try:
                jobs = await self.scrape_company(company["name"], company["careers_url"], limit)
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"Error scraping {company['name']}: {e}")
        
        return all_jobs
    
    def _generate_job_description(self, role: str, skills: List[str], company: str) -> str:
        """Generate realistic-looking job description"""
        template = random.choice(self.job_descriptions)
        
        tech = ", ".join(skills[:2])
        scale = random.choice(["100M+", "1B+", "10B+"])
        team = random.choice(["platform", "product", "infrastructure", "research"])
        
        jd = template.format(tech=tech, role=role, team=team, scale=scale)
        
        # Add requirements
        jd += f"\n\nRequirements:\n"
        jd += f"- {random.randint(3, 8)}+ years of experience\n"
        jd += f"- Strong knowledge of {', '.join(skills)}\n"
        jd += f"- System design and architecture experience\n"
        jd += f"- Experience at scale (100M+ users)\n"
        
        # Add nice-to-haves
        jd += f"\n\nNice to have:\n"
        jd += f"- Open source contributions\n"
        jd += f"- Published papers or talks\n"
        jd += f"- Previous experience at {random.choice(['FAANG', 'top startups', 'high-growth companies'])}\n"
        
        return jd
    
    async def scrape_single_job(self, url: str) -> Optional[Dict]:
        """Mock scrape a single job from URL"""
        await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # Parse domain to infer company
        domain_match = None
        for company_name in ["Google", "Microsoft", "Meta", "Amazon", "Apple"]:
            if company_name.lower() in url.lower():
                domain_match = company_name
                break
        
        company = domain_match or "Unknown Company"
        
        template = random.choice(self.demo_jobs_templates)
        
        return {
            "title": random.choice(template["titles"]),
            "company": company,
            "location": random.choice(self.locations),
            "salary_min": template["salary_min"],
            "salary_max": template["salary_max"],
            "is_remote": random.choice([True, False]),
            "link": url,
            "jd_text": self._generate_job_description(random.choice(template["titles"]),
                                                      random.sample(template["skills"], 3),
                                                      company),
            "posted_date": datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
            "source": company
        }
    
    def scrape_from_text(self, job_description_text: str, company_name: str = "Manual Entry") -> Optional[Dict]:
        """Parse manually entered job description text"""
        # Try to extract key info from text
        lines = job_description_text.split('\n')
        
        # Try to find title (usually first line or after "Title:")
        title = "Job Title"
        for line in lines[:5]:
            if any(kw in line for kw in ["title", "engineer", "manager", "specialist"]):
                title = line.replace("title:", "").replace("Title:", "").strip()
                break
        
        # Try to find salary
        salary_min, salary_max = 100000, 200000
        import re
        salary_match = re.search(r'\$?([\d,]+)\s*-\s*\$?([\d,]+)', job_description_text)
        if salary_match:
            try:
                salary_min = int(salary_match.group(1).replace(',', ''))
                salary_max = int(salary_match.group(2).replace(',', ''))
            except:
                pass
        
        return {
            "title": title,
            "company": company_name,
            "location": "TBD",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "is_remote": "remote" in job_description_text.lower(),
            "link": "manual-entry",
            "jd_text": job_description_text,
            "posted_date": datetime.now(timezone.utc),
            "source": company_name
        }


# Global scraper instance
scraper = MockScraper()


async def run_scraper_demo():
    """Demo the scraper"""
    companies = [
        {"name": "Google", "careers_url": "https://www.google.com/careers"},
        {"name": "Meta", "careers_url": "https://www.metacareers.com"}
    ]
    
    jobs = await scraper.scrape_multiple_companies(companies, limit=2)
    
    for job in jobs:
        print(f"✓ {job['title']} at {job['company']}")
    
    return jobs


if __name__ == "__main__":
    jobs = asyncio.run(run_scraper_demo())
    print(f"\n✅ Scraped {len(jobs)} mock jobs")
