"""
Database module for JobForge.
Handles SQLite operations using SQLAlchemy.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

# Database file paths
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
JOBS_DB = os.path.join(DB_DIR, "jobs.db")
PROFILES_DB = os.path.join(DB_DIR, "profiles.db")

# Ensure data directory exists
os.makedirs(DB_DIR, exist_ok=True)


class Job(Base):
    """Job posting model"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(10), default="USD")
    job_type = Column(String(50))  # Full-time, Contract, etc.
    is_remote = Column(Boolean, default=False)
    link = Column(String(1024), unique=True, nullable=False)
    jd_text = Column(Text)  # Full job description
    posted_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source = Column(String(100))  # Where we scraped from
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Profile(Base):
    """User profile model"""
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True)
    user_name = Column(String(255))
    current_title = Column(String(255))
    years_experience = Column(Integer, default=0)
    summary = Column(Text)
    skills = Column(Text)  # JSON string of skills list
    education = Column(Text)  # JSON string
    resume_text = Column(Text)  # Full resume text
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobMetric(Base):
    """Tracks match scores for each job per user"""
    __tablename__ = "job_metrics"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer)
    match_score = Column(Float, default=0.0)  # 0-100
    semantic_score = Column(Float, default=0.0)  # Embedding-based
    openai_score = Column(Float, default=0.0)  # If OpenAI was used
    viewed = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class JobAlert(Base):
    """Alert configuration for job searches (Phase 1)"""
    __tablename__ = "job_alerts"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))  # e.g., "Senior Python Engineer @ FAANG"
    keywords = Column(Text)  # JSON array of keywords
    companies = Column(Text)  # JSON array of company names
    min_salary = Column(Integer)
    max_salary = Column(Integer)
    location = Column(String(255))
    remote_only = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    email_notify = Column(Boolean, default=True)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db(db_path=JOBS_DB):
    """Initialize database and create tables"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path=JOBS_DB):
    """Get SQLAlchemy session"""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def seed_demo_jobs():
    """Seed database with demo job data"""
    session = get_session(JOBS_DB)
    
    # Check if data already exists
    if session.query(Job).count() > 0:
        return  # Already seeded
    
    demo_jobs = [
        Job(
            title="Senior Software Engineer",
            company="Google",
            location="Mountain View, CA",
            salary_min=180000,
            salary_max=250000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://www.google.com/careers/jobs/000001",
            jd_text="""We are seeking a Senior Software Engineer to join our core infrastructure team. 
            You will work on large-scale distributed systems serving billions of users.
            Requirements: 7+ years Python/Go experience, distributed systems knowledge, strong CS fundamentals.
            Python, Go, Kubernetes, Microservices.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=2),
            source="Google Careers"
        ),
        Job(
            title="Machine Learning Engineer",
            company="Meta",
            location="Menlo Park, CA",
            salary_min=200000,
            salary_max=280000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://www.metacareers.com/jobs/000002",
            jd_text="""Join Meta's AI Research team working on next-generation large language models.
            You will design and implement novel ML architectures and train models at scale.
            Requirements: 5+ years ML experience, PyTorch proficiency, publication record preferred.
            Python, PyTorch, CUDA, Transformers.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=1),
            source="Meta Careers"
        ),
        Job(
            title="Full Stack Engineer",
            company="Stripe",
            location="San Francisco, CA",
            salary_min=175000,
            salary_max=240000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://stripe.com/jobs/000003",
            jd_text="""Build payment infrastructure trusted by millions. You will work across mobile, web, and backend.
            Requirements: 4+ years full-stack experience, React or Vue.js, Node.js or Python backend.
            React, Node.js, PostgreSQL, AWS.""",
            posted_date=datetime.now(timezone.utc),
            source="Stripe Careers"
        ),
        Job(
            title="Cloud Architect",
            company="Microsoft",
            location="Seattle, WA",
            salary_min=165000,
            salary_max=220000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://careers.microsoft.com/jobs/000004",
            jd_text="""Design and implement Azure cloud solutions for enterprise clients.
            Requirements: 8+ years cloud architecture, Azure certifications, Terraform/Ansible.
            Azure, Kubernetes, Terraform, Python.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=3),
            source="Microsoft Careers"
        ),
        Job(
            title="Data Engineer",
            company="Palantir",
            location="Palo Alto, CA",
            salary_min=185000,
            salary_max=260000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://www.palantir.com/careers/000005",
            jd_text="""Build scalable data pipelines processing petabytes of data.
            Requirements: 5+ years data engineering, Spark/Flink, SQL optimization.
            Python, Scala, Spark, SQL.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=5),
            source="Palantir Careers"
        ),
        Job(
            title="Frontend Engineer",
            company="Figma",
            location="San Francisco, CA",
            salary_min=160000,
            salary_max=230000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://figma.com/jobs/000006",
            jd_text="""Work on Figma's web editor and real-time collaboration features.
            Requirements: 4+ years React, strong performance optimization skills, WebGL or Canvas experience.
            React, TypeScript, WebGL, Node.js.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=7),
            source="Figma Careers"
        ),
        Job(
            title="DevOps Engineer",
            company="Netflix",
            location="Los Gatos, CA",
            salary_min=170000,
            salary_max=245000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://jobs.netflix.com/000007",
            jd_text="""Manage Netflix's infrastructure serving 200M+ users globally.
            Requirements: 6+ years DevOps, AWS/GCP expertise, Go or Python scripting, no fear of chaos engineering.
            Go, AWS, Kubernetes, Python.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=4),
            source="Netflix Careers"
        ),
        Job(
            title="Product Manager",
            company="Notion",
            location="San Francisco, CA",
            salary_min=150000,
            salary_max=220000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://notion.so/jobs/000008",
            jd_text="""Lead product strategy for a new Notion vertical. Impact millions of knowledge workers.
            Requirements: 4+ years PM experience, strong analytics mindset, technical background preferred.
            Product Management, Analytics, Roadmapping.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=6),
            source="Notion Careers"
        ),
        Job(
            title="Security Engineer",
            company="Apple",
            location="Cupertino, CA",
            salary_min=170000,
            salary_max=240000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://jobs.apple.com/000009",
            jd_text="""Secure Apple's infrastructure and products. Work on cutting-edge security challenges.
            Requirements: 7+ years security engineering, cryptography knowledge, C/Rust preferred.
            C, Rust, Python, Cryptography.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=8),
            source="Apple Careers"
        ),
        Job(
            title="AI Researcher",
            company="OpenAI",
            location="San Francisco, CA",
            salary_min=200000,
            salary_max=300000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://openai.com/careers/000010",
            jd_text="""Advance the frontier of AI safety and capabilities. Work on GPT-5 and beyond.
            Requirements: PhD in ML/CS or equivalent, publication record, CUDA expertise.
            Python, PyTorch, CUDA, Math/Statistics.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=1),
            source="OpenAI Careers"
        ),
        Job(
            title="Backend Engineer",
            company="Amazon",
            location="Seattle, WA",
            salary_min=155000,
            salary_max=225000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=False,
            link="https://amazon.jobs/000011",
            jd_text="""Build services powering AWS. Scale to handle trillions of requests.
            Requirements: 5+ years backend experience, Java or C++, async systems knowledge.
            Java, C++, Python, AWS.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=2),
            source="Amazon Careers"
        ),
        Job(
            title="Infrastructure Engineer",
            company="Vercel",
            location="San Francisco, CA",
            salary_min=160000,
            salary_max=235000,
            salary_currency="USD",
            job_type="Full-time",
            is_remote=True,
            link="https://vercel.com/jobs/000012",
            jd_text="""Build the infrastructure layer for the Web. Work on edge computing, serverless, and more.
            Requirements: 4+ years infrastructure, Go or Rust, distributed systems.
            Go, Rust, JavaScript, Linux.""",
            posted_date=datetime.now(timezone.utc) - timedelta(days=10),
            source="Vercel Careers"
        ),
    ]
    
    session.add_all(demo_jobs)
    session.commit()
    
    # Seed job metrics for each job
    jobs = session.query(Job).all()
    for job in jobs:
        # Assign demo match scores
        import random
        metric = JobMetric(
            job_id=job.id,
            semantic_score=random.uniform(60, 95),
            match_score=random.uniform(65, 98),
            viewed=random.choice([True, False]),
            saved=random.choice([True, False, False])
        )
        session.add(metric)
    
    session.commit()
    session.close()


def create_alert(name: str, keywords: list = None, companies: list = None, 
                min_salary: int = None, max_salary: int = None, 
                location: str = None, remote_only: bool = False) -> JobAlert:
    """Create a new job alert"""
    import json
    session = get_session()
    alert = JobAlert(
        name=name,
        keywords=json.dumps(keywords or []),
        companies=json.dumps(companies or []),
        min_salary=min_salary,
        max_salary=max_salary,
        location=location,
        remote_only=remote_only
    )
    session.add(alert)
    session.commit()
    session.close()
    return alert


def get_alerts(enabled_only: bool = True) -> list:
    """Get all alerts"""
    session = get_session()
    query = session.query(JobAlert)
    if enabled_only:
        query = query.filter_by(enabled=True)
    alerts = query.all()
    session.close()
    return alerts


if __name__ == "__main__":
    init_db()
    seed_demo_jobs()
    print(f"✅ Database initialized at {JOBS_DB}")
