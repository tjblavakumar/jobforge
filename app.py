"""
JobForge Phase 3 - Personal Job Search Co-Pilot
A clean, locally-deployable Streamlit app for tech job search.
"""

import streamlit as st
import pandas as pd
import json
import os
import asyncio
import textwrap
from datetime import datetime, timedelta, timezone
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from db import init_db, get_session, Job, Profile, JobMetric, seed_demo_jobs
from resume_parser import parse_resume, mock_parse_resume
from scraper import scraper
from matching import get_matcher, simple_matcher

try:
    from real_scraper import scrape_companies as scrape_companies_real, PlaywrightScraper
    HAS_REAL_SCRAPER = True
except Exception:
    HAS_REAL_SCRAPER = False

try:
    from openai_integration import get_analyzer, validate_api_key
    HAS_OPENAI_INTEGRATION = True
except Exception:
    HAS_OPENAI_INTEGRATION = False

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="JobForge - Job Search Co-Pilot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
    <style>
    /* Main Theme */
    :root {
        --primary: #2563eb;
        --primary-dark: #1d4ed8;
        --secondary: #60a5fa;
        --danger: #ef4444;      /* Red */
        --bg-light: #f9fafb;    /* Light gray */
        --text-dark: #111827;   /* Very dark gray */
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        background-color: var(--bg-light);
    }

    [data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e5e7eb;
    }

    .job-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin: 0.75rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .job-card:hover {
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
        border-color: var(--primary);
    }

    .job-card.high-match {
        border-left: 4px solid var(--primary);
        background: linear-gradient(90deg, rgba(37,99,235,0.06) 0%, white 100%);
    }

    .job-card.medium-match {
        border-left: 4px solid var(--secondary);
        background: linear-gradient(90deg, rgba(96,165,250,0.08) 0%, white 100%);
    }

    .match-score {
        display: inline-block;
        font-weight: 700;
        font-size: 1.25rem;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
    }

    .match-score.high {
        background-color: #dbeafe;
        color: #1e3a8a;
    }

    .match-score.medium {
        background-color: #e0e7ff;
        color: #3730a3;
    }

    .match-score.low {
        background-color: #fee2e2;
        color: #7f1d1d;
    }

    .stProgress > div > div > div {
        background-color: var(--primary) !important;
    }

    .stButton > button {
        background-color: var(--primary) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
    }

    .stButton > button:hover {
        background-color: var(--primary-dark) !important;
    }

    h1, h2, h3 {
        color: var(--text-dark) !important;
    }

    h1 {
        border-bottom: 3px solid var(--primary);
        padding-bottom: 0.75rem;
    }

    .skill-chip {
        display: inline-block;
        background-color: #eff6ff;
        color: #1e3a8a;
        border: 1px solid #bfdbfe;
        padding: 0.375rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 500;
        margin: 0.25rem;
    }

    .stat-box {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1.5rem;
        text-align: center;
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
    }

    .stat-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.5rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 0.65rem !important;
        border-color: #dbe3ef !important;
        background-color: #ffffff !important;
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        [data-testid="stAppViewContainer"] {
            background-color: #0f172a !important;
        }

        [data-testid="stSidebar"] {
            background-color: #111827 !important;
            border-right: 1px solid #1f2937 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #111827 !important;
            border-color: #1f2937 !important;
        }

        .stat-box {
            background: #111827 !important;
            border-color: #1f2937 !important;
            box-shadow: none;
        }

        .stat-label, .stCaption {
            color: #9ca3af !important;
        }

        h1, h2, h3, h4, p, span, label, div {
            color: #e5e7eb;
        }

        .skill-chip {
            background-color: #1e293b;
            color: #bfdbfe;
            border-color: #334155;
        }

        .job-card {
            background: #111827;
            border-color: #1f2937;
            box-shadow: none;
        }
    }

    /* Streamlit dark theme fallback selectors */
    [data-theme="dark"] [data-testid="stSidebar"],
    [data-theme="dark"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-theme="dark"] .stat-box {
        background-color: #111827 !important;
        border-color: #1f2937 !important;
    }
    
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "profile_loaded" not in st.session_state:
    st.session_state.profile_loaded = False
if "jobs_data" not in st.session_state:
    st.session_state.jobs_data = None
if "filter_salary_min" not in st.session_state:
    st.session_state.filter_salary_min = 100000
if "filter_salary_max" not in st.session_state:
    st.session_state.filter_salary_max = 300000

# Initialize database
init_db()
seed_demo_jobs()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@st.cache_resource
def get_db_session():
    """Get database session"""
    return get_session()

def load_jobs_from_db():
    """Load all jobs from database"""
    session = get_db_session()
    
    jobs_query = session.query(Job).all()
    jobs = []
    
    for job in jobs_query:
        # Get the associated metric
        metric = session.query(JobMetric).filter_by(job_id=job.id).first()
        
        job_dict = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "is_remote": job.is_remote,
            "link": job.link,
            "jd_text": job.jd_text[:500] + "..." if job.jd_text and len(job.jd_text) > 500 else job.jd_text,
            "jd_full": job.jd_text,
            "posted_date": job.posted_date,
            "source": job.source,
            "viewed": metric.viewed if metric else False,
            "saved": metric.saved if metric else False,
            "match_score": metric.match_score if metric else 0,
        }
        jobs.append(job_dict)
    
    return jobs

def get_user_profile():
    """Get or create user profile"""
    session = get_db_session()
    profile = session.query(Profile).first()
    
    if not profile:
        profile = Profile(user_name="User")
        session.add(profile)
        session.commit()
    
    return {
        "name": profile.user_name or "User",
        "title": profile.current_title or "Professional",
        "years_exp": profile.years_experience or 0,
        "skills": json.loads(profile.skills) if profile.skills else [],
        "summary": profile.summary or "",
        "education": json.loads(profile.education) if profile.education else []
    }

def save_profile(data):
    """Save profile to database"""
    session = get_db_session()
    profile = session.query(Profile).first()
    
    if not profile:
        profile = Profile()
    
    profile.user_name = data.get("name", "User")
    profile.current_title = data.get("title", "")
    profile.years_experience = data.get("years_exp", 0)
    profile.skills = json.dumps(data.get("skills", []))
    profile.summary = data.get("summary", "")
    profile.education = json.dumps(data.get("education", []))
    
    session.merge(profile)
    session.commit()

def get_settings():
    """Get settings from st.secrets or env"""
    if "openai_key_override" in st.session_state:
        openai_key = st.session_state.get("openai_key_override", "")
    else:
        openai_key = st.secrets.get("OPENAI_API_KEY", "")

    settings = {
        "openai_key": openai_key,
        "location": st.secrets.get("LOCATION", "US"),
        "min_salary": st.secrets.get("MIN_SALARY", 100000),
        "exp_level": st.secrets.get("EXP_LEVEL", "senior"),
        "blacklist": st.secrets.get("BLACKLIST", "").split(",") if st.secrets.get("BLACKLIST") else []
    }
    return settings

def save_settings(settings):
    """Save settings (would go to .streamlit/secrets.toml in production)"""
    st.info("⚠️ Settings are read-only in Phase 3. Use `.streamlit/secrets.toml` to configure.")

def get_search_presets_path():
    """Path for persisted dashboard search presets"""
    return os.path.join(os.path.dirname(__file__), "data", "search_presets.json")

def load_search_presets():
    """Load saved dashboard search presets"""
    path = get_search_presets_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def save_search_presets(presets):
    """Persist dashboard search presets"""
    path = get_search_presets_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)

def get_salary_range_display(min_sal, max_sal):
    """Format salary range"""
    if min_sal and max_sal:
        return f"${min_sal:,} - ${max_sal:,}"
    elif min_sal:
        return f"${min_sal:,}+"
    else:
        return "Undisclosed"

def format_date(date_obj):
    """Format date for display"""
    if not date_obj:
        return "Recently"
    # Ensure date_obj is timezone-aware
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    days_ago = (datetime.now(timezone.utc) - date_obj).days
    if days_ago == 0:
        return "Today"
    elif days_ago == 1:
        return "Yesterday"
    elif days_ago < 7:
        return f"{days_ago} days ago"
    elif days_ago < 30:
        return f"{days_ago // 7} weeks ago"
    else:
        return f"{days_ago // 30} months ago"


def run_async_task(coro):
    """Safely run async coroutine from Streamlit callbacks."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
    except RuntimeError:
        pass
    return asyncio.run(coro)


async def scrape_single_job_real_async(url: str, company_name: str = "Unknown"):
    """Scrape a single job URL with Playwright scraper."""
    scraper_instance = PlaywrightScraper(headless=True)
    await scraper_instance.initialize()
    try:
        return await scraper_instance.scrape_job_post(url, company_name=company_name)
    finally:
        await scraper_instance.close()


def persist_jobs(jobs):
    """Insert/update scraped jobs and compute match scores."""
    if not jobs:
        return 0, 0

    session = get_db_session()
    profile = get_user_profile()
    settings = get_settings()
    api_key = (settings.get("openai_key") or "").strip()
    use_openai = bool(api_key)
    matcher = get_matcher(use_openai=use_openai, api_key=api_key if use_openai else None)
    inserted = 0
    updated = 0

    for job in jobs:
        if not job:
            continue

        link = job.get("link") or f"manual-{job.get('company', 'company')}-{job.get('title', 'role')}"
        existing = session.query(Job).filter_by(link=link).first()

        if existing:
            db_job = existing
            updated += 1
        else:
            db_job = Job(link=link)
            inserted += 1

        db_job.title = job.get("title", "Job Position")
        db_job.company = job.get("company", "Unknown Company")
        db_job.location = job.get("location", "Unknown")
        db_job.salary_min = job.get("salary_min") or 0
        db_job.salary_max = job.get("salary_max") or 0
        db_job.is_remote = bool(job.get("is_remote", False))
        db_job.jd_text = job.get("jd_text", "")
        db_job.posted_date = job.get("posted_date") or datetime.now(timezone.utc)
        db_job.source = job.get("source", db_job.company)

        session.merge(db_job)
        session.flush()

        score, breakdown = matcher.score_job(
            {
                "title": db_job.title,
                "company": db_job.company,
                "location": db_job.location,
                "salary_min": db_job.salary_min,
                "salary_max": db_job.salary_max,
                "is_remote": db_job.is_remote,
                "jd_text": db_job.jd_text,
            },
            {
                "title": profile.get("title", "Professional"),
                "years_exp": profile.get("years_exp", 0),
                "skills": profile.get("skills", []),
                "summary": profile.get("summary", ""),
                "prefer_remote": True,
                "expected_salary_min": int(settings.get("min_salary", 100000)),
                "expected_salary_max": int(settings.get("min_salary", 100000)) + 150000,
            }
        )

        metric = session.query(JobMetric).filter_by(job_id=db_job.id).first()
        if not metric:
            metric = JobMetric(job_id=db_job.id)
            session.add(metric)

        metric.match_score = float(score)
        metric.semantic_score = float(breakdown.get("semantic_match", 0))
        metric.openai_score = float(breakdown.get("openai_score", 0))

    session.commit()
    return inserted, updated


def update_job_openai_metric(job_id: int, openai_score: float):
    """Persist OpenAI score for a specific job metric."""
    session = get_db_session()
    metric = session.query(JobMetric).filter_by(job_id=job_id).first()
    if not metric:
        metric = JobMetric(job_id=job_id, match_score=0.0)
        session.add(metric)

    metric.openai_score = float(openai_score)
    metric.match_score = max(0.0, min(100.0, (metric.match_score * 0.95) + (openai_score * 0.05)))
    session.commit()


def rescore_all_jobs_with_openai(api_key: str, progress_callback=None):
    """Re-score all existing jobs using matcher with OpenAI enabled."""
    api_key = (api_key or "").strip()
    if not api_key:
        return 0, 0.0

    session = get_db_session()
    profile = get_user_profile()
    settings = get_settings()
    matcher = get_matcher(use_openai=True, api_key=api_key)

    jobs = session.query(Job).all()
    if not jobs:
        session.close()
        return 0, 0.0

    total_score = 0.0
    processed = 0
    total_jobs = len(jobs)

    if progress_callback:
        progress_callback(0, total_jobs, None)

    for idx, db_job in enumerate(jobs, start=1):
        score, breakdown = matcher.score_job(
            {
                "title": db_job.title,
                "company": db_job.company,
                "location": db_job.location,
                "salary_min": db_job.salary_min,
                "salary_max": db_job.salary_max,
                "is_remote": db_job.is_remote,
                "jd_text": db_job.jd_text,
            },
            {
                "title": profile.get("title", "Professional"),
                "years_exp": profile.get("years_exp", 0),
                "skills": profile.get("skills", []),
                "summary": profile.get("summary", ""),
                "prefer_remote": True,
                "expected_salary_min": int(settings.get("min_salary", 100000)),
                "expected_salary_max": int(settings.get("min_salary", 100000)) + 150000,
            }
        )

        metric = session.query(JobMetric).filter_by(job_id=db_job.id).first()
        if not metric:
            metric = JobMetric(job_id=db_job.id)
            session.add(metric)

        metric.match_score = float(score)
        metric.semantic_score = float(breakdown.get("semantic_match", 0))
        metric.openai_score = float(breakdown.get("openai_score", 0))

        total_score += float(score)
        processed += 1

        if progress_callback:
            progress_callback(idx, total_jobs, db_job)

    session.commit()
    session.close()
    return processed, (total_score / processed if processed else 0.0)

# ============================================================================
# PAGE COMPONENTS
# ============================================================================

def page_dashboard():
    """Dashboard with job cards and filters"""
    st.title("💼 Dashboard")
    
    jobs = load_jobs_from_db()
    user_profile = get_user_profile()
    settings = get_settings()
    openai_key = (settings.get("openai_key") or "").strip()
    openai_enabled = bool(openai_key and HAS_OPENAI_INTEGRATION)
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{len(jobs)}</div>
            <div class="stat-label">Total Jobs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        saved_count = sum(1 for j in jobs if j["saved"])
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{saved_count}</div>
            <div class="stat-label">Saved Jobs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        high_match = sum(1 for j in jobs if j["match_score"] >= 70)
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{high_match}</div>
            <div class="stat-label">High Match (70+)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_score = sum(j["match_score"] for j in jobs) / len(jobs) if jobs else 0
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{avg_score:.0f}</div>
            <div class="stat-label">Avg Match Score</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filters
    st.subheader("🔍 Filters")
    st.caption("Phase 3: Save, load, and reuse search filter presets.")

    available_companies = sorted(list(set(j["company"] for j in jobs)))
    presets = load_search_presets()

    if "dash_salary_min" not in st.session_state:
        st.session_state.dash_salary_min = 100000
    if "dash_salary_max" not in st.session_state:
        st.session_state.dash_salary_max = 300000
    if "dash_remote_only" not in st.session_state:
        st.session_state.dash_remote_only = False
    if "dash_companies" not in st.session_state:
        st.session_state.dash_companies = []
    if "dash_freshness_days" not in st.session_state:
        st.session_state.dash_freshness_days = 30
    if "dash_sort_option" not in st.session_state:
        st.session_state.dash_sort_option = "Best Match"

    st.session_state.dash_companies = [
        c for c in st.session_state.dash_companies if c in available_companies
    ]

    preset_cols = st.columns([0.45, 0.2, 0.35])
    with preset_cols[0]:
        selected_preset = st.selectbox(
            "Saved Presets",
            ["(none)"] + sorted(list(presets.keys())),
            key="dash_preset_selector"
        )
    with preset_cols[1]:
        load_preset = st.button("📥 Load", use_container_width=True)
    with preset_cols[2]:
        delete_preset = st.button("🗑️ Delete Selected", use_container_width=True)

    save_cols = st.columns([0.7, 0.3])
    with save_cols[0]:
        new_preset_name = st.text_input("Preset Name", key="dash_new_preset_name")
    with save_cols[1]:
        save_preset = st.button("💾 Save Preset", use_container_width=True)

    if load_preset:
        if selected_preset == "(none)":
            st.warning("Select a preset to load.")
        else:
            preset = presets.get(selected_preset, {})
            st.session_state.dash_salary_min = int(preset.get("salary_min", 100000))
            st.session_state.dash_salary_max = int(preset.get("salary_max", 300000))
            st.session_state.dash_remote_only = bool(preset.get("remote_only", False))
            st.session_state.dash_companies = [
                c for c in preset.get("companies", []) if c in available_companies
            ]
            st.session_state.dash_freshness_days = int(preset.get("freshness_days", 30))
            st.session_state.dash_sort_option = preset.get("sort_by", "Best Match")
            st.success(f"Loaded preset: {selected_preset}")
            st.rerun()

    if delete_preset:
        if selected_preset == "(none)":
            st.warning("Select a preset to delete.")
        elif selected_preset not in presets:
            st.warning("Preset not found.")
        else:
            presets.pop(selected_preset, None)
            save_search_presets(presets)
            st.success(f"Deleted preset: {selected_preset}")
            st.rerun()

    if save_preset:
        preset_name = (new_preset_name or "").strip()
        if not preset_name:
            st.warning("Enter a preset name before saving.")
        else:
            presets[preset_name] = {
                "salary_min": int(st.session_state.dash_salary_min),
                "salary_max": int(st.session_state.dash_salary_max),
                "remote_only": bool(st.session_state.dash_remote_only),
                "companies": list(st.session_state.dash_companies),
                "freshness_days": int(st.session_state.dash_freshness_days),
                "sort_by": st.session_state.dash_sort_option
            }
            save_search_presets(presets)
            st.success(f"Saved preset: {preset_name}")

    filter_cols = st.columns(5)

    with filter_cols[0]:
        st.slider("💰 Min Salary", 50000, 300000, step=10000, key="dash_salary_min")

    with filter_cols[1]:
        st.slider("💰 Max Salary", 100000, 400000, step=10000, key="dash_salary_max")

    with filter_cols[2]:
        st.checkbox("🌍 Remote Only", key="dash_remote_only")

    with filter_cols[3]:
        st.multiselect("🏢 Companies", options=available_companies, key="dash_companies")

    with filter_cols[4]:
        st.slider("📅 Posted within (days)", 1, 90, key="dash_freshness_days")

    salary_min = st.session_state.dash_salary_min
    salary_max = st.session_state.dash_salary_max
    remote_only = st.session_state.dash_remote_only
    companies = st.session_state.dash_companies
    freshness_days = st.session_state.dash_freshness_days

    st.markdown("**Sort**")
    st.radio(
        "Sort by",
        ["Best Match", "Newest", "Highest Salary"],
        horizontal=True,
        key="dash_sort_option",
        label_visibility="collapsed"
    )
    sort_option = st.session_state.dash_sort_option
    
    # Apply filters
    filtered_jobs = jobs
    
    if salary_min:
        filtered_jobs = [j for j in filtered_jobs if not j["salary_max"] or j["salary_max"] >= salary_min]
    
    if salary_max:
        filtered_jobs = [j for j in filtered_jobs if not j["salary_min"] or j["salary_min"] <= salary_max]
    
    if remote_only:
        filtered_jobs = [j for j in filtered_jobs if j["is_remote"]]
    
    if companies:
        filtered_jobs = [j for j in filtered_jobs if j["company"] in companies]
    
    if freshness_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=freshness_days)
        filtered_jobs = [j for j in filtered_jobs if j["posted_date"] and (
            j["posted_date"].replace(tzinfo=timezone.utc) if j["posted_date"].tzinfo is None else j["posted_date"]
        ) >= cutoff]
    
    # Sort jobs
    if sort_option == "Newest":
        filtered_jobs.sort(
            key=lambda x: (
                x["posted_date"].replace(tzinfo=timezone.utc)
                if x.get("posted_date") and x["posted_date"].tzinfo is None
                else x.get("posted_date")
            )
            or datetime(1970, 1, 1, tzinfo=timezone.utc),
            reverse=True
        )
    elif sort_option == "Highest Salary":
        filtered_jobs.sort(
            key=lambda x: (x.get("salary_max") or x.get("salary_min") or 0),
            reverse=True
        )
    else:
        filtered_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    selected_companies_summary = "All companies"
    if companies:
        if len(companies) <= 3:
            selected_companies_summary = ", ".join(companies)
        else:
            selected_companies_summary = f"{', '.join(companies[:3])} +{len(companies) - 3} more"

    active_filters = [
        f"Sort: {sort_option}",
        f"Salary: ${salary_min:,}-${salary_max:,}",
        f"Remote: {'On' if remote_only else 'Off'}",
        f"Companies: {selected_companies_summary}",
        f"Freshness: {freshness_days} days",
    ]
    
    st.markdown("---")
    st.caption(" | ".join(active_filters))
    st.subheader(f"📋 Jobs ({len(filtered_jobs)} / {len(jobs)})")
    
    if not filtered_jobs:
        st.info("😔 No jobs match your filters. Try adjusting them!")
    else:
        for job in filtered_jobs:
            match_score = job.get("match_score", 0)
            salary_display = get_salary_range_display(job["salary_min"], job["salary_max"])
            posted = format_date(job["posted_date"])
            remote_badge = " • 🌍 Remote" if job["is_remote"] else ""

            with st.container(border=True):
                header_col1, header_col2 = st.columns([0.78, 0.22])
                with header_col1:
                    st.markdown(f"### {job['title']}")
                    st.caption(f"{job['company']} • {job['location']}{remote_badge}")
                with header_col2:
                    st.metric("Match", f"{match_score:.0f}%")

                meta_col1, meta_col2, meta_col3 = st.columns(3)
                with meta_col1:
                    st.caption(f"💵 {salary_display}")
                with meta_col2:
                    st.caption(f"📅 {posted}")
                with meta_col3:
                    st.caption(f"🏷️ {job.get('source', 'Unknown')}")

                if job.get("jd_text"):
                    with st.expander("📄 View Details"):
                        st.markdown(f"**Full Job Description:**\n\n{job['jd_full'][:1000]}...")
                        if job["link"] and job["link"] != "manual-entry":
                            st.markdown(f"[🔗 View Original]({job['link']})")

                        if openai_enabled:
                            ai_col1, ai_col2 = st.columns(2)
                            with ai_col1:
                                if st.button("🤖 Analyze Match", key=f"ai_match_{job['id']}"):
                                    with st.spinner("Running OpenAI match analysis..."):
                                        analyzer = get_analyzer(openai_key)
                                        if analyzer and analyzer.client:
                                            score, reasoning = analyzer.score_job_match(job, user_profile)
                                            st.session_state[f"ai_match_result_{job['id']}"] = (
                                                f"OpenAI Score: {score:.0f}/100\n\n{reasoning}"
                                            )
                                            update_job_openai_metric(job["id"], score)
                                        else:
                                            st.warning("OpenAI is not configured correctly.")

                            with ai_col2:
                                if st.button("🎯 Interview Prep", key=f"ai_prep_{job['id']}"):
                                    with st.spinner("Generating interview prep..."):
                                        analyzer = get_analyzer(openai_key)
                                        if analyzer and analyzer.client:
                                            prep = analyzer.generate_interview_prep(job)
                                            st.session_state[f"ai_prep_result_{job['id']}"] = prep
                                        else:
                                            st.warning("OpenAI is not configured correctly.")

                            if st.session_state.get(f"ai_match_result_{job['id']}"):
                                st.markdown("**OpenAI Match Analysis**")
                                st.info(st.session_state.get(f"ai_match_result_{job['id']}"))

                            if st.session_state.get(f"ai_prep_result_{job['id']}"):
                                st.markdown("**Interview Prep**")
                                st.markdown(st.session_state.get(f"ai_prep_result_{job['id']}"))
                        else:
                            st.caption("Add an OpenAI API key in Settings to enable AI analysis and interview prep.")

                action_col1, action_col2, action_col3, action_col4 = st.columns(4)
                with action_col1:
                    if job["link"] and job["link"] != "manual-entry":
                        st.link_button("🔗 Open", job["link"], use_container_width=True)
                    else:
                        st.button("🔗 Open", disabled=True, use_container_width=True, key=f"open_disabled_{job['id']}")
                with action_col2:
                    if st.button("💾 Save", key=f"save_{job['id']}", use_container_width=True):
                        st.success("✅ Saved!")
                with action_col3:
                    if st.button("✓ View", key=f"view_{job['id']}", use_container_width=True):
                        st.info(f"Marked as viewed: {job['title']}")
                with action_col4:
                    if st.button("❌ Remove", key=f"reject_{job['id']}", use_container_width=True):
                        st.info(f"Rejected {job['title']}")


def page_profile():
    """Profile setup page"""
    st.title("👤 Your Profile")
    
    profile = get_user_profile()
    
    st.subheader("📄 Resume Upload")
    uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        parsed_data = parse_resume(file_bytes, uploaded_file.name, use_openai=False)
        
        st.success("✅ Resume parsed successfully!")
        st.json(parsed_data)
        
        if parsed_data["success"]:
            profile = {
                "name": profile.get("name", "User"),
                "title": parsed_data.get("current_title", profile.get("title", "Professional")),
                "years_exp": parsed_data.get("years_experience", profile.get("years_exp", 0)),
                "skills": parsed_data.get("skills", profile.get("skills", [])),
                "summary": parsed_data.get("summary", profile.get("summary", "")),
                "education": parsed_data.get("education", profile.get("education", []))
            }
    
    st.markdown("---")
    st.subheader("✏️ Edit Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Name", value=profile.get("name", "User"))
        title = st.text_input("Current Title", value=profile.get("title", "Professional"))
        years_exp = st.number_input("Years of Experience", value=profile.get("years_exp", 0), min_value=0, max_value=60)
    
    with col2:
        summary = st.text_area("Professional Summary", value=profile.get("summary", ""), height=100)
    
    st.markdown("**Skills**")
    skills_input = st.text_input("Skills (comma-separated)", value=", ".join(profile.get("skills", [])))
    skills = [s.strip() for s in skills_input.split(",") if s.strip()]
    
    # Display skills as chips
    if skills:
        st.markdown("**Your Skills:**")
        skills_html = " ".join([f'<span class="skill-chip">{skill}</span>' for skill in skills])
        st.markdown(skills_html, unsafe_allow_html=True)
    
    st.markdown("**Education**")
    education_input = st.text_area("Education (one per line)", value="\n".join(profile.get("education", [])), height=80)
    education = [e.strip() for e in education_input.split("\n") if e.strip()]
    
    if st.button("💾 Save Profile", use_container_width=True):
        profile_data = {
            "name": name,
            "title": title,
            "years_exp": years_exp,
            "skills": skills,
            "summary": summary,
            "education": education
        }
        save_profile(profile_data)
        st.success("✅ Profile saved!")


def page_companies():
    """Browse and scan preferred companies"""
    st.title("🏢 Preferred Companies")

    def is_california_job(job: dict) -> bool:
        location = (job.get("location") or "").lower()
        if "california" in location or ", ca" in location:
            return True
        ca_cities = ["sacramento", "los angeles", "san diego", "oakland", "san francisco", "fresno", "san jose"]
        return any(city in location for city in ca_cities)

    def normalize_url(url: str) -> str:
        cleaned = (url or "").strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            cleaned = f"https://{cleaned}"
        return cleaned

    def validate_url(url: str, check_reachability: bool = True):
        normalized = normalize_url(url)
        parsed = urlparse(normalized)

        if not normalized:
            return False, "URL is empty.", normalized
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False, "URL must be a valid http/https address.", normalized

        if not check_reachability:
            return True, "URL format looks valid.", normalized

        try:
            request = Request(
                normalized,
                headers={"User-Agent": "Mozilla/5.0 (JobForge URL Validator)"},
                method="HEAD"
            )
            with urlopen(request, timeout=8) as response:
                status_code = getattr(response, "status", response.getcode())
            if 200 <= status_code < 400:
                return True, f"URL reachable (HTTP {status_code}).", normalized
            return False, f"URL returned HTTP {status_code}.", normalized
        except HTTPError as exc:
            if exc.code in {401, 403, 405, 429}:
                return True, f"URL appears valid (HTTP {exc.code} from server).", normalized
            return False, f"URL check failed (HTTP {exc.code}).", normalized
        except URLError as exc:
            return False, f"URL check failed: {exc.reason}", normalized
        except Exception as exc:
            return False, f"URL check failed: {str(exc)[:120]}", normalized
    
    def load_companies(companies_path: str) -> list:
        if os.path.exists(companies_path):
            with open(companies_path, "r", encoding="utf-8") as f:
                companies_data = json.load(f)
                return companies_data.get("companies", [])[:100]
        return []

    def save_companies(companies_path: str, companies: list):
        with open(companies_path, "w", encoding="utf-8") as f:
            json.dump({"companies": companies}, f, indent=2, ensure_ascii=False)

    companies_path = os.path.join(os.path.dirname(__file__), "data", "companies.json")
    companies = load_companies(companies_path)

    st.subheader("⚙️ Manage Companies")
    manage_col1, manage_col2 = st.columns(2)

    with manage_col1:
        with st.form("add_company_form", clear_on_submit=True):
            st.markdown("**Add Company**")
            new_name = st.text_input("Company Name")
            new_url = st.text_input("Careers URL")
            new_industry = st.text_input("Industry", value="Technology")
            new_logo = st.text_input("Logo", value="🏢")
            new_state = st.text_input("State (optional)", value="")

            add_col1, add_col2 = st.columns(2)
            with add_col1:
                validate_new_url = st.form_submit_button("🔎 Validate URL", use_container_width=True)
            with add_col2:
                submitted_add = st.form_submit_button("➕ Add Company", use_container_width=True)

            if validate_new_url:
                is_valid_url, validation_message, normalized_new_url = validate_url(new_url, check_reachability=True)
                if is_valid_url:
                    st.success(f"{validation_message}\n\nNormalized: {normalized_new_url}")
                else:
                    st.error(validation_message)

            if submitted_add:
                name = new_name.strip()
                careers_url = normalize_url(new_url)
                industry = new_industry.strip() or "Technology"
                logo = new_logo.strip() or "🏢"
                state = new_state.strip().upper()

                is_valid_url, validation_message, careers_url = validate_url(careers_url, check_reachability=True)

                if not name or not careers_url:
                    st.error("Company Name and Careers URL are required.")
                elif not is_valid_url:
                    st.error(validation_message)
                elif any(c.get("name", "").lower() == name.lower() for c in companies):
                    st.warning("Company already exists.")
                else:
                    next_id = (max((c.get("id", 0) for c in companies), default=0) + 1)
                    new_company = {
                        "id": next_id,
                        "name": name,
                        "careers_url": careers_url,
                        "industry": industry,
                        "logo": logo
                    }
                    if state:
                        new_company["state"] = state

                    companies.append(new_company)
                    save_companies(companies_path, companies)
                    st.success(f"Added {name}.")
                    st.rerun()

    with manage_col2:
        st.markdown("**Delete Company**")
        company_names = [c.get("name", "") for c in companies]
        if not company_names:
            st.caption("No companies to delete.")
        else:
            delete_name = st.selectbox("Select Company to Delete", company_names)
            if st.button("🗑️ Delete Company", use_container_width=True):
                updated_companies = [c for c in companies if c.get("name") != delete_name]
                save_companies(companies_path, updated_companies)
                st.success(f"Deleted {delete_name}.")
                st.rerun()

    st.markdown("---")
    st.subheader("🔗 Validate Existing Careers URL")
    if companies:
        validate_company_name = st.selectbox(
            "Select company",
            [c.get("name", "") for c in companies],
            key="validate_company_name"
        )
        selected_company_for_validation = next(
            (c for c in companies if c.get("name") == validate_company_name),
            None
        )
        if selected_company_for_validation:
            selected_url = selected_company_for_validation.get("careers_url", "")
            st.caption(f"Current URL: {selected_url}")
            if st.button("✅ Validate Selected URL", use_container_width=False):
                is_valid_url, validation_message, normalized_url = validate_url(selected_url, check_reachability=True)
                if is_valid_url:
                    st.success(f"{validation_message} | {normalized_url}")
                else:
                    st.error(validation_message)
    else:
        st.caption("No companies available to validate.")

    company_location_filter = st.selectbox(
        "Location Filter",
        ["All", "California Only"],
        help="Filter company cards and scans to California-focused sources."
    )

    filtered_companies = companies
    if company_location_filter == "California Only":
        filtered_companies = [
            company for company in companies
            if company.get("state") == "CA"
            or "california" in company.get("name", "").lower()
            or "ca.gov" in company.get("careers_url", "").lower()
            or "calcareers" in company.get("careers_url", "").lower()
        ]

    if not filtered_companies:
        st.info("No companies match the current location filter.")
    
    st.markdown("---")
    
    # Display companies in grid
    cols = st.columns(4)
    for i, company in enumerate(filtered_companies):
        with cols[i % 4]:
            careers_url = normalize_url(company.get("careers_url", ""))
            st.markdown(f"""
            <div style="
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 0.5rem;
                padding: 1rem;
                text-align: center;
                margin: 0.5rem 0;
                cursor: pointer;
                transition: all 0.3s;
            ">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{company['logo']}</div>
                <h4 style="margin: 0.5rem 0; font-size: 0.9rem;">{company['name']}</h4>
                <p style="margin: 0.25rem 0; font-size: 0.75rem; color: #9ca3af;">{company['industry']}</p>
            </div>
            """, unsafe_allow_html=True)
            if careers_url:
                st.link_button("🔗 Open Careers", careers_url, use_container_width=True)
            else:
                st.caption("No careers URL configured.")
    
    st.markdown("---")
    st.subheader("🔄 Scan for Open Roles")

    use_real_scraper = st.checkbox(
        "Use Real Scraper (Playwright)",
        value=st.session_state.get("use_real_scraper", False),
        help="When enabled, attempts real web scraping and falls back to mock if unavailable."
    )
    st.session_state.use_real_scraper = use_real_scraper
    max_jobs = st.slider("Max jobs per company", min_value=1, max_value=5, value=2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Scan All Companies", use_container_width=True):
            progress_bar = st.progress(0)
            progress_status = st.empty()

            total_companies = len(filtered_companies)
            jobs = []

            if total_companies == 0:
                progress_status.text("No companies configured to scan.")
                st.info("No companies found in data source.")
            else:
                for idx, company in enumerate(filtered_companies, start=1):
                    progress_status.text(f"Scanning {idx}/{total_companies}: {company['name']}")
                    company_jobs = []

                    if use_real_scraper and HAS_REAL_SCRAPER:
                        try:
                            company_jobs = scrape_companies_real([company], max_jobs_per_company=max_jobs)
                        except Exception as e:
                            st.warning(f"Real scraper unavailable for {company['name']}, using mock mode. Reason: {str(e)[:120]}")

                    if not company_jobs:
                        company_jobs = run_async_task(
                            scraper.scrape_company(company["name"], company["careers_url"], limit=max_jobs)
                        )

                    if company_location_filter == "California Only":
                        company_jobs = [job for job in company_jobs if is_california_job(job)]

                    jobs.extend(company_jobs)
                    progress_bar.progress(int((idx / total_companies) * 85))

                progress_status.text("Persisting scanned jobs to database...")
                progress_bar.progress(92)
                inserted, updated = persist_jobs(jobs)
                progress_bar.progress(100)
                progress_status.text(f"Completed {total_companies}/{total_companies} companies.")

                st.success(f"✅ Scan complete: {len(jobs)} jobs processed ({inserted} new, {updated} updated).")
    
    with col2:
        selected_company_options = [c["name"] for c in filtered_companies]
        if not selected_company_options:
            st.caption("No companies available for the selected filter.")
            return

        selected_company = st.selectbox("Select Company", selected_company_options)
        if st.button("🔍 Scan Single Company", use_container_width=True):
            company = next((c for c in filtered_companies if c["name"] == selected_company), None)
            if not company:
                st.error("Selected company not found.")
                return

            progress_bar = st.progress(0)
            progress_status = st.empty()
            progress_status.text(f"Scanning {selected_company}...")
            progress_bar.progress(15)

            jobs = []
            if use_real_scraper and HAS_REAL_SCRAPER:
                try:
                    jobs = scrape_companies_real([company], max_jobs_per_company=max_jobs)
                except Exception as e:
                    st.warning(f"Real scraper unavailable, using mock mode. Reason: {str(e)[:120]}")

            if not jobs:
                jobs = run_async_task(scraper.scrape_company(company["name"], company["careers_url"], limit=max_jobs))

            if company_location_filter == "California Only":
                jobs = [job for job in jobs if is_california_job(job)]

            progress_status.text("Persisting scanned jobs to database...")
            progress_bar.progress(90)
            inserted, updated = persist_jobs(jobs)

            progress_bar.progress(100)
            progress_status.text(f"Completed scan for {selected_company}.")
            st.success(f"✅ {selected_company} scan complete: {len(jobs)} jobs ({inserted} new, {updated} updated).")


def page_add_job():
    """Manually add a job"""
    st.title("➕ Add Job Manually")
    
    tab1, tab2 = st.tabs(["Paste URL", "Paste Job Description"])
    
    with tab1:
        st.subheader("Paste Job URL")
        url = st.text_input("Job URL")
        use_real_scraper = st.checkbox(
            "Use Real Scraper for URL",
            value=st.session_state.get("use_real_scraper", False)
        )
        
        if url and st.button("🔍 Scrape from URL"):
            st.info("🔄 Scraping job from URL...")
            job = None

            if use_real_scraper and HAS_REAL_SCRAPER:
                try:
                    job = run_async_task(scrape_single_job_real_async(url))
                except Exception as e:
                    st.warning(f"Real scraper failed, falling back to mock. Reason: {str(e)[:120]}")

            if not job:
                job = run_async_task(scraper.scrape_single_job(url))

            if job:
                inserted, updated = persist_jobs([job])
                st.success("✅ Job scraped successfully!")
                st.json(job)
                st.caption(f"Database sync: {inserted} new, {updated} updated")
    
    with tab2:
        st.subheader("Paste Full Job Description")
        jd_text = st.text_area("Job Description", height=300)
        company_name = st.text_input("Company Name (optional)")
        
        if jd_text and st.button("💾 Add Job from Text"):
            job = scraper.scrape_from_text(jd_text, company_name or "Manual Entry")
            inserted, updated = persist_jobs([job])
            st.success("✅ Job added to database!")
            st.json(job)
            st.caption(f"Database sync: {inserted} new, {updated} updated")


def page_settings():
    """Settings page"""
    st.title("⚙️ Settings")
    
    settings = get_settings()
    
    st.subheader("🔑 OpenAI API Key")
    openai_key = st.text_input("OpenAI API Key", value=settings.get("openai_key", ""), type="password")
    key_source = "session" if "openai_key_override" in st.session_state else "secrets"
    st.caption(f"Current key source: {key_source}")
    
    if openai_key != settings.get("openai_key", ""):
        st.info("✅ API key configured! (set in `.streamlit/secrets.toml`)")
    
    st.subheader("📍 Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        location = st.text_input("Preferred Location", value=settings.get("location", "US"))
        min_salary = st.number_input("Min Salary", value=int(settings.get("min_salary", 100000)), step=10000)
    
    with col2:
        exp_level = st.selectbox("Experience Level", 
                                 ["junior", "mid", "senior", "staff", "lead"],
                                 index=["junior", "mid", "senior", "staff", "lead"].index(settings.get("exp_level", "senior")))
        prefer_remote = st.checkbox("Prefer Remote", value=True)
    
    st.subheader("🚫 Blacklist")
    blacklist = st.text_area("Companies to Exclude (one per line)", 
                             value="\n".join(settings.get("blacklist", [])))

    st.subheader("🧠 AI Re-scoring")
    has_openai = bool(openai_key.strip() and HAS_OPENAI_INTEGRATION)
    if not HAS_OPENAI_INTEGRATION:
        st.caption("OpenAI integration module not available.")
    elif not openai_key.strip():
        st.caption("Add an OpenAI API key above to enable bulk re-scoring.")

    if st.button("🔄 Re-score All Jobs (OpenAI)", use_container_width=True, disabled=not has_openai):
        progress_bar = st.progress(0)
        progress_status = st.empty()

        def on_progress(current, total, job):
            progress = int((current / total) * 100) if total else 100
            progress_bar.progress(min(max(progress, 0), 100))
            if current == 0:
                progress_status.text("Starting OpenAI re-scoring...")
            elif job:
                progress_status.text(f"Processing {current}/{total}: {job.title} @ {job.company}")
            else:
                progress_status.text(f"Processing {current}/{total}...")

        processed, avg_score = rescore_all_jobs_with_openai(openai_key.strip(), progress_callback=on_progress)
        progress_bar.progress(100)
        if processed:
            progress_status.text(f"Completed {processed}/{processed} jobs.")
            st.success(f"✅ Re-scored {processed} jobs. New average match score: {avg_score:.1f}%")
        else:
            progress_status.text("No jobs found to re-score.")
            st.info("No jobs found to re-score.")
    
    if st.button("💾 Save Settings", use_container_width=True):
        st.session_state.openai_key_override = openai_key.strip()

        if openai_key.strip() and HAS_OPENAI_INTEGRATION:
            with st.spinner("Validating OpenAI key..."):
                if validate_api_key(openai_key.strip()):
                    st.success("✅ Settings saved for this session and OpenAI key is valid.")
                else:
                    st.warning("⚠️ Settings saved for this session, but OpenAI key validation failed.")
        else:
            st.success("✅ Settings saved for this session.")


# ============================================================================
# MAIN APP LAYOUT
# ============================================================================

def main():
    """Main app layout"""
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h2 style="margin: 0; display: flex; align-items: center;">
                <span style="font-size: 1.5rem; margin-right: 0.5rem;">💼</span>
                <span>JobForge</span>
            </h2>
            <p style="margin: 0.5rem 0 0 0; color: #9ca3af; font-size: 0.85rem;">Phase 3 - Smart Search</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation menu
        nav_items = [
            ("Dashboard", "💼 Dashboard"),
            ("Profile", "👤 Profile"),
            ("Preferred Companies", "🏢 Preferred Companies"),
            ("Add Job", "➕ Add Job"),
            ("Settings", "⚙️ Settings"),
        ]

        if st.session_state.page not in [item[0] for item in nav_items]:
            st.session_state.page = "Dashboard"

        for page_key, page_label in nav_items:
            is_active = st.session_state.page == page_key
            if st.button(
                page_label,
                key=f"nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.page = page_key
                st.rerun()
        
        st.markdown("---")
        
        # Sidebar info
        st.subheader("📊 Quick Stats")
        jobs = load_jobs_from_db()
        st.metric("Total Jobs", len(jobs))
        st.metric("Avg Match Score", f"{sum(j['match_score'] for j in jobs) / len(jobs) if jobs else 0:.0f}%")
        
        st.markdown("---")
        
        # Help
        with st.expander("❓ Help", expanded=False):
            st.markdown("""
            **Welcome to JobForge!**
            
            1. **Upload Your Resume** → Profile page
            2. **Set Preferences** → Settings page
            3. **Add Companies** → Preferred Companies
            4. **Browse Jobs** → Dashboard
            5. **Open Jobs** → Use original job links
            
            Made with ❤️ for tech job seekers.
            """)
    
    # Main content
    if st.session_state.page == "Dashboard":
        page_dashboard()
    elif st.session_state.page == "Profile":
        page_profile()
    elif st.session_state.page == "Preferred Companies":
        page_companies()
    elif st.session_state.page == "Add Job":
        page_add_job()
    elif st.session_state.page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
