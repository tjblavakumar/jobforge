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
import io
import smtplib
from datetime import datetime, timedelta, timezone
import sys
from email.message import EmailMessage
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

try:
    import fitz
    HAS_PDF_EXPORT = True
except Exception:
    HAS_PDF_EXPORT = False

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
    st.session_state.page = "Get Started"
if "profile_loaded" not in st.session_state:
    st.session_state.profile_loaded = False
if "jobs_data" not in st.session_state:
    st.session_state.jobs_data = None
if "filter_salary_min" not in st.session_state:
    st.session_state.filter_salary_min = 100000
if "filter_salary_max" not in st.session_state:
    st.session_state.filter_salary_max = 300000
if "scrape_mode_real" not in st.session_state:
    st.session_state.scrape_mode_real = False
if "pending_real_mode" not in st.session_state:
    st.session_state.pending_real_mode = False
if "scrape_mode_request" not in st.session_state:
    st.session_state.scrape_mode_request = st.session_state.scrape_mode_real
if "suppress_real_mode_prompt" not in st.session_state:
    st.session_state.suppress_real_mode_prompt = False

# Initialize database
init_db()
if os.getenv("ENABLE_DEMO_SEED", "false").strip().lower() in {"1", "true", "yes", "on"}:
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
    """Get or create active user profile."""
    session = get_db_session()
    selected_profile_id = st.session_state.get("active_profile_id")
    profile = None
    if selected_profile_id:
        profile = session.query(Profile).filter_by(id=selected_profile_id).first()

    if not profile:
        profile = session.query(Profile).order_by(Profile.id.asc()).first()
    
    if not profile:
        profile = Profile(user_name="User")
        session.add(profile)
        session.commit()

    st.session_state.active_profile_id = profile.id
    
    return {
        "id": profile.id,
        "name": profile.user_name or "User",
        "title": profile.current_title or "Professional",
        "years_exp": profile.years_experience or 0,
        "skills": json.loads(profile.skills) if profile.skills else [],
        "summary": profile.summary or "",
        "education": json.loads(profile.education) if profile.education else []
    }


def list_profiles():
    """Return all profiles as normalized dictionaries."""
    session = get_db_session()
    profiles = session.query(Profile).order_by(Profile.id.asc()).all()

    normalized = []
    for profile in profiles:
        normalized.append(
            {
                "id": profile.id,
                "name": profile.user_name or f"Profile {profile.id}",
                "title": profile.current_title or "Professional",
                "years_exp": profile.years_experience or 0,
                "skills": json.loads(profile.skills) if profile.skills else [],
                "summary": profile.summary or "",
                "education": json.loads(profile.education) if profile.education else [],
            }
        )
    return normalized

def save_profile(data, profile_id=None):
    """Save profile to database."""
    session = get_db_session()
    profile = None
    if profile_id:
        profile = session.query(Profile).filter_by(id=profile_id).first()

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
    st.session_state.active_profile_id = profile.id

def get_settings():
    """Get settings from st.secrets or env"""
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = {}

    def _get_value(key, default=""):
        value = secrets.get(key)
        if value is None or value == "":
            value = os.getenv(key, default)
        return value

    def _get_int_value(key, default):
        value = _get_value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _get_bool_value(key, default=False):
        value = _get_value(key, str(default))
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    if "openai_key_override" in st.session_state:
        openai_key = st.session_state.get("openai_key_override", "")
    else:
        openai_key = _get_value("OPENAI_API_KEY", "")

    blacklist_raw = _get_value("BLACKLIST", "")
    if isinstance(blacklist_raw, list):
        blacklist = [str(item).strip() for item in blacklist_raw if str(item).strip()]
    else:
        blacklist = [item.strip() for item in str(blacklist_raw).split(",") if item.strip()]

    settings = {
        "openai_key": openai_key,
        "location": _get_value("LOCATION", "US"),
        "min_salary": _get_int_value("MIN_SALARY", 100000),
        "min_match_score": _get_int_value("MIN_MATCH_SCORE", 50),
        "exp_level": _get_value("EXP_LEVEL", "senior"),
        "blacklist": blacklist,
        "alerts_enabled": _get_bool_value("ALERTS_ENABLED", False),
        "alert_min_score": _get_int_value("ALERT_MIN_SCORE", 80),
        "alert_max_items": _get_int_value("ALERT_MAX_ITEMS", 10),
        "smtp_host": _get_value("SMTP_HOST", ""),
        "smtp_port": _get_int_value("SMTP_PORT", 587),
        "smtp_user": _get_value("SMTP_USER", ""),
        "smtp_password": _get_value("SMTP_PASSWORD", ""),
        "alert_email_to": _get_value("ALERT_EMAIL_TO", ""),
        "alert_email_from": _get_value("ALERT_EMAIL_FROM", "")
    }

    session_override = st.session_state.get("settings_override")
    if isinstance(session_override, dict):
        settings.update(session_override)

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


def get_source_validation_path():
    """Path for source validation status records."""
    return os.path.join(os.path.dirname(__file__), "data", "source_validation.json")


def load_source_validation():
    """Load source validation records."""
    path = get_source_validation_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_source_validation(records):
    """Persist source validation records."""
    path = get_source_validation_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def record_source_validation(company: dict, mode: str, jobs_count: int, success: bool, detail: str = ""):
    """Upsert source validation status for a company."""
    records = load_source_validation()
    key = str(company.get("id") or company.get("name") or "unknown")
    records[key] = {
        "company": company.get("name", "Unknown"),
        "url": company.get("careers_url", ""),
        "mode": mode,
        "success": bool(success),
        "jobs_count": int(jobs_count),
        "detail": detail,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    save_source_validation(records)


def scan_company_jobs(company: dict, use_real_scraper: bool, max_jobs: int, max_concurrency: int):
    """Scan a single company and return jobs + status metadata."""
    mode = "real" if use_real_scraper else "mock"
    jobs = []
    detail = ""

    if use_real_scraper:
        if not HAS_REAL_SCRAPER:
            detail = "Playwright scraper unavailable"
            return jobs, {"success": False, "mode": mode, "detail": detail}
        try:
            jobs = scrape_companies_real(
                [company],
                max_jobs_per_company=max_jobs,
                max_concurrency=max_concurrency,
            )
            detail = "ok" if jobs else "No valid job-detail pages found"
            return jobs, {"success": bool(jobs), "mode": mode, "detail": detail}
        except Exception as exc:
            detail = str(exc)[:180]
            return jobs, {"success": False, "mode": mode, "detail": detail}

    jobs = run_async_task(scraper.scrape_company(company["name"], company["careers_url"], limit=max_jobs))
    detail = "ok" if jobs else "No jobs returned by mock scraper"
    return jobs, {"success": bool(jobs), "mode": mode, "detail": detail}

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


async def scrape_mock_companies_parallel(companies, limit=2, max_concurrency=5):
    """Scrape multiple companies in parallel using mock scraper."""
    safe_concurrency = max(1, int(max_concurrency))
    semaphore = asyncio.Semaphore(safe_concurrency)

    async def scrape_one(company):
        async with semaphore:
            try:
                jobs = await scraper.scrape_company(company["name"], company["careers_url"], limit=limit)
            except Exception:
                jobs = []
            return company.get("name", "Unknown"), jobs

    tasks = [scrape_one(company) for company in companies]
    results = await asyncio.gather(*tasks)
    return {company_name: jobs for company_name, jobs in results}


def get_alert_state_path():
    """Path for persisted job alert state."""
    return os.path.join(os.path.dirname(__file__), "data", "alerts_state.json")


def load_alert_state():
    """Load persisted alert state."""
    path = get_alert_state_path()
    if not os.path.exists(path):
        return {"seen_job_ids": [], "last_checked_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
            if not isinstance(state, dict):
                return {"seen_job_ids": [], "last_checked_at": None}
            state.setdefault("seen_job_ids", [])
            state.setdefault("last_checked_at", None)
            return state
    except Exception:
        return {"seen_job_ids": [], "last_checked_at": None}


def save_alert_state(state):
    """Persist alert state to disk."""
    path = get_alert_state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_new_alert_jobs(min_score=80, max_items=10):
    """Find unseen jobs above threshold score."""
    jobs = load_jobs_from_db()
    state = load_alert_state()
    seen_ids = {int(job_id) for job_id in state.get("seen_job_ids", []) if str(job_id).isdigit()}

    candidates = [
        job for job in jobs
        if int(job.get("id", 0) or 0) not in seen_ids and float(job.get("match_score", 0)) >= float(min_score)
    ]

    candidates.sort(
        key=lambda x: (
            x.get("posted_date") or datetime(1970, 1, 1, tzinfo=timezone.utc),
            float(x.get("match_score", 0))
        ),
        reverse=True
    )
    return candidates[:max(1, int(max_items))]


def mark_alert_jobs_seen(jobs):
    """Mark alert jobs as seen to avoid duplicate alerts."""
    state = load_alert_state()
    seen_ids = set(state.get("seen_job_ids", []))
    for job in jobs:
        job_id = int(job.get("id", 0) or 0)
        if job_id:
            seen_ids.add(job_id)
    state["seen_job_ids"] = sorted(seen_ids)
    state["last_checked_at"] = datetime.now(timezone.utc).isoformat()
    save_alert_state(state)


def send_job_alert_email(jobs, settings):
    """Send job alerts via SMTP when settings are configured."""
    smtp_host = (settings.get("smtp_host") or "").strip()
    smtp_port = int(settings.get("smtp_port") or 587)
    smtp_user = (settings.get("smtp_user") or "").strip()
    smtp_password = (settings.get("smtp_password") or "").strip()
    email_to = (settings.get("alert_email_to") or "").strip()
    email_from = (settings.get("alert_email_from") or smtp_user).strip()

    if not jobs:
        return False, "No new jobs to send."
    if not smtp_host or not email_to or not email_from:
        return False, "SMTP/email settings missing (SMTP_HOST, ALERT_EMAIL_TO, ALERT_EMAIL_FROM)."

    lines = [
        f"JobForge found {len(jobs)} new high-match jobs:",
        ""
    ]
    for idx, job in enumerate(jobs, start=1):
        salary = get_salary_range_display(job.get("salary_min"), job.get("salary_max"))
        posted = format_date(job.get("posted_date"))
        lines.append(
            f"{idx}. {job.get('title', 'Job')} @ {job.get('company', 'Company')} | "
            f"Match {float(job.get('match_score', 0)):.0f}% | {salary} | {posted}"
        )
        if job.get("link") and job.get("link") != "manual-entry":
            lines.append(f"   {job['link']}")
    body = "\n".join(lines)

    msg = EmailMessage()
    msg["Subject"] = f"JobForge Alerts: {len(jobs)} New Matches"
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True, f"Alert email sent to {email_to}."
    except Exception as exc:
        return False, f"Email send failed: {str(exc)[:140]}"


def jobs_to_export_rows(jobs):
    """Normalize job rows for exports."""
    rows = []
    for job in jobs:
        posted_date = job.get("posted_date")
        posted_iso = ""
        if posted_date:
            if getattr(posted_date, "tzinfo", None) is None:
                posted_date = posted_date.replace(tzinfo=timezone.utc)
            posted_iso = posted_date.isoformat()

        rows.append(
            {
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "salary_min": job.get("salary_min") or 0,
                "salary_max": job.get("salary_max") or 0,
                "match_score": round(float(job.get("match_score", 0)), 2),
                "is_remote": bool(job.get("is_remote", False)),
                "posted_date": posted_iso,
                "source": job.get("source", ""),
                "link": job.get("link", ""),
            }
        )
    return rows


def export_jobs_csv_bytes(jobs):
    """Create CSV bytes for job list export."""
    rows = jobs_to_export_rows(jobs)
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def export_jobs_pdf_bytes(jobs):
    """Create PDF bytes for job list export."""
    if not HAS_PDF_EXPORT:
        return None

    rows = jobs_to_export_rows(jobs)
    doc = fitz.open()

    page = doc.new_page()
    page_width = page.rect.width
    page_height = page.rect.height
    margin = 36
    y = margin
    line_height = 14
    max_y = page_height - margin

    def add_line(text):
        nonlocal page, y
        if y + line_height > max_y:
            page = doc.new_page()
            y = margin
        page.insert_text((margin, y), text, fontsize=10)
        y += line_height

    header = f"JobForge Export | Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    add_line(header)
    add_line(f"Total Jobs: {len(rows)}")
    add_line("-" * int((page_width - margin * 2) / 6))

    for idx, row in enumerate(rows, start=1):
        salary = get_salary_range_display(row.get("salary_min"), row.get("salary_max"))
        heading = (
            f"{idx}. {row.get('title', 'Job')} @ {row.get('company', 'Company')} "
            f"| Match {row.get('match_score', 0):.0f}%"
        )
        add_line(heading)
        add_line(f"   {row.get('location', 'Unknown')} | {salary} | Remote: {'Yes' if row.get('is_remote') else 'No'}")
        if row.get("link"):
            for wrapped in textwrap.wrap(str(row.get("link")), width=95):
                add_line(f"   {wrapped}")
        add_line("")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def is_real_scrape_mode():
    """Global scrape mode from sidebar toggle."""
    return bool(st.session_state.get("scrape_mode_real", False))


def remove_mock_jobs_from_db():
    """Best-effort cleanup of mock-generated jobs and related metrics."""
    session = get_db_session()
    jobs = session.query(Job).all()
    mock_job_ids = []

    for job in jobs:
        source = (job.source or "").lower()
        link = (job.link or "").lower()
        jd_text = (job.jd_text or "").lower()

        looks_like_mock_source = "mock" in source or "[mock]" in source
        looks_like_mock_link = "/job-" in link and "careers" not in source
        looks_like_mock_template = "nice to have" in jd_text and "open source contributions" in jd_text

        if looks_like_mock_source or looks_like_mock_link or looks_like_mock_template:
            mock_job_ids.append(job.id)

    if not mock_job_ids:
        return 0

    session.query(JobMetric).filter(JobMetric.job_id.in_(mock_job_ids)).delete(synchronize_session=False)
    session.query(Job).filter(Job.id.in_(mock_job_ids)).delete(synchronize_session=False)
    session.commit()
    return len(mock_job_ids)


async def scrape_single_job_real_async(url: str, company_name: str = "Unknown"):
    """Scrape a single job URL with Playwright scraper."""
    scraper_instance = PlaywrightScraper(headless=True)
    await scraper_instance.initialize()
    try:
        return await scraper_instance.scrape_job_post(url, company_name=company_name)
    finally:
        await scraper_instance.close()


def persist_jobs(jobs, selected_profiles=None):
    """Insert/update scraped jobs and compute match scores."""
    if not jobs:
        return 0, 0

    session = get_db_session()
    profiles = selected_profiles or [get_user_profile()]
    if not profiles:
        profiles = [get_user_profile()]
    settings = get_settings()
    min_match_score = float(settings.get("min_match_score", 50))
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

        candidate_title = job.get("title", "Job Position")
        candidate_company = job.get("company", "Unknown Company")
        candidate_location = job.get("location", "Unknown")
        candidate_salary_min = job.get("salary_min") or 0
        candidate_salary_max = job.get("salary_max") or 0
        candidate_is_remote = bool(job.get("is_remote", False))
        candidate_jd_text = job.get("jd_text", "")
        candidate_posted_date = job.get("posted_date") or datetime.now(timezone.utc)

        source_value = job.get("source", candidate_company)
        data_mode = str(job.get("data_mode", "")).strip().lower()
        if data_mode == "mock" and "mock" not in str(source_value).lower():
            source_value = f"{source_value} [Mock]"
        elif data_mode == "real" and "real" not in str(source_value).lower():
            source_value = f"{source_value} [Real]"

        best_score = 0.0
        best_breakdown = {"semantic_match": 0.0, "openai_score": 0.0}

        candidate_job_payload = {
            "title": candidate_title,
            "company": candidate_company,
            "location": candidate_location,
            "salary_min": candidate_salary_min,
            "salary_max": candidate_salary_max,
            "is_remote": candidate_is_remote,
            "jd_text": candidate_jd_text,
        }

        for profile in profiles:
            score, breakdown = matcher.score_job(
                candidate_job_payload,
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
            if float(score) >= float(best_score):
                best_score = float(score)
                best_breakdown = breakdown or {"semantic_match": 0.0, "openai_score": 0.0}

        if float(best_score) < float(min_match_score):
            if existing:
                session.query(JobMetric).filter_by(job_id=existing.id).delete(synchronize_session=False)
                session.query(Job).filter_by(id=existing.id).delete(synchronize_session=False)
            continue

        if existing:
            db_job = existing
            updated += 1
        else:
            db_job = Job(link=link)
            inserted += 1

        db_job.title = candidate_title
        db_job.company = candidate_company
        db_job.location = candidate_location
        db_job.salary_min = candidate_salary_min
        db_job.salary_max = candidate_salary_max
        db_job.is_remote = candidate_is_remote
        db_job.jd_text = candidate_jd_text
        db_job.posted_date = candidate_posted_date
        db_job.source = source_value

        session.merge(db_job)
        session.flush()

        metric = session.query(JobMetric).filter_by(job_id=db_job.id).first()
        if not metric:
            metric = JobMetric(job_id=db_job.id)
            session.add(metric)

        metric.match_score = float(best_score)
        metric.semantic_score = float(best_breakdown.get("semantic_match", 0))
        metric.openai_score = float(best_breakdown.get("openai_score", 0))

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


def set_job_saved(job_id: int, saved: bool = True):
    """Persist saved state for a specific job metric."""
    session = get_db_session()
    metric = session.query(JobMetric).filter_by(job_id=job_id).first()
    if not metric:
        metric = JobMetric(job_id=job_id)
        session.add(metric)
    metric.saved = bool(saved)
    session.commit()


def delete_job_by_id(job_id: int):
    """Delete a job and its associated metric."""
    session = get_db_session()
    session.query(JobMetric).filter_by(job_id=job_id).delete(synchronize_session=False)
    deleted = session.query(Job).filter_by(id=job_id).delete(synchronize_session=False)
    session.commit()
    return bool(deleted)


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

def page_get_started():
    """First-run onboarding wizard page."""
    st.title("🏠 Home")
    st.caption("Follow these steps in order to use JobForge effectively.")

    profile = get_user_profile()
    all_profiles = list_profiles()
    jobs = load_jobs_from_db()

    companies_path = os.path.join(os.path.dirname(__file__), "data", "companies.json")
    companies_count = 0
    if os.path.exists(companies_path):
        try:
            with open(companies_path, "r", encoding="utf-8") as f:
                companies_data = json.load(f)
                companies_count = len(companies_data.get("companies", []))
        except Exception:
            companies_count = 0

    has_profile = bool(profile.get("title") and profile.get("skills"))
    has_companies = companies_count > 0
    has_jobs = len(jobs) > 0

    completed_steps = sum([has_profile, has_companies, has_jobs])
    progress = completed_steps / 3
    st.progress(progress)
    st.caption(f"Progress: {completed_steps}/3 core setup steps completed")

    step1_col1, step1_col2 = st.columns([0.78, 0.22])
    with step1_col1:
        st.markdown("### 1) Build Your Profile")
        st.caption("Upload resume and confirm skills/title for better match scoring.")
        st.caption("Status: ✅ Complete" if has_profile else "Status: ⏳ Not complete")
    with step1_col2:
        if st.button("Go to Profile", use_container_width=True):
            st.session_state.page = "Profile"
            st.rerun()

    step2_col1, step2_col2 = st.columns([0.78, 0.22])
    with step2_col1:
        st.markdown("### 2) Configure Sources")
        st.caption("Review companies and run scans to pull open roles into your database.")
        st.caption("Status: ✅ Complete" if has_companies else "Status: ⏳ Not complete")
    with step2_col2:
        if st.button("Go to Companies", use_container_width=True):
            st.session_state.page = "Preferred Companies"
            st.rerun()

    step3_col1, step3_col2 = st.columns([0.78, 0.22])
    with step3_col1:
        st.markdown("### 3) Review and Act")
        st.caption("Use Dashboard filters, save presets, analyze with OpenAI, and export results.")
        st.caption("Status: ✅ Complete" if has_jobs else "Status: ⏳ Not complete")
    with step3_col2:
        st.button("View Results Below", use_container_width=True, disabled=True)

    st.markdown("---")
    st.subheader("Recommended Flow")
    st.markdown(
        "1. Profile → 2. Settings (OpenAI optional) → 3. Preferred Companies → 4. Scan + review results on Home"
    )

    quick_col1, quick_col2 = st.columns(2)
    with quick_col1:
        if st.button("⚙️ Open Settings", use_container_width=True):
            st.session_state.page = "Settings"
            st.rerun()
    with quick_col2:
        if st.button("➕ Add Job Manually", use_container_width=True):
            st.session_state.page = "Add Job"
            st.rerun()

    st.markdown("---")
    st.subheader("🔄 Scan Active Companies for Matching Jobs")
    use_real_scraper = is_real_scrape_mode()
    st.caption(
        "Real Scraper Mode: ON" if use_real_scraper else "Real Scraper Mode: OFF (mock generation)"
    )

    companies_path = os.path.join(os.path.dirname(__file__), "data", "companies.json")
    companies = []
    if os.path.exists(companies_path):
        try:
            with open(companies_path, "r", encoding="utf-8") as f:
                companies_data = json.load(f)
                companies = companies_data.get("companies", [])[:100]
        except Exception:
            companies = []

    active_companies = [company for company in companies if bool(company.get("active", True))]
    if not active_companies:
        st.info("No active companies found. Activate companies in Preferred Companies page first.")
        st.markdown("---")
        page_dashboard(show_title=False, show_back_button=False)
        return

    profile_options = [f"{p['name']} (ID {p['id']})" for p in all_profiles]
    profile_label_to_id = {f"{p['name']} (ID {p['id']})": p["id"] for p in all_profiles}

    selected_profile_labels = st.multiselect(
        "Select Profiles for Matching",
        options=profile_options,
        default=profile_options[:1] if profile_options else [],
        key="gs_selected_profiles"
    )
    selected_profile_ids = [profile_label_to_id[label] for label in selected_profile_labels]
    selected_profiles = [p for p in all_profiles if p.get("id") in selected_profile_ids]

    if not selected_profiles:
        st.warning("Select at least one profile before scanning.")
        st.markdown("---")
        page_dashboard(show_title=False, show_back_button=False)
        return

    max_jobs = st.slider("Max jobs per company", min_value=1, max_value=5, value=2, key="gs_max_jobs")
    max_concurrency = st.slider("Parallel scans", min_value=1, max_value=8, value=4, key="gs_max_concurrency")

    scan_col1, scan_col2 = st.columns(2)

    with scan_col1:
        st.markdown("**Scan Single Company**")
        selected_company = st.selectbox(
            "Select Active Company",
            [c["name"] for c in active_companies],
            key="gs_selected_company"
        )
        if st.button("🔍 Scan Selected Company", use_container_width=True, key="gs_scan_single"):
            company = next((c for c in active_companies if c["name"] == selected_company), None)
            if not company:
                st.error("Selected company not found.")
            else:
                progress_bar = st.progress(0)
                progress_status = st.empty()
                progress_status.text(f"Scanning {selected_company}...")
                progress_bar.progress(15)

                jobs, status = scan_company_jobs(company, use_real_scraper, max_jobs, max_concurrency)
                record_source_validation(
                    company,
                    mode=status.get("mode", "real" if use_real_scraper else "mock"),
                    jobs_count=len(jobs),
                    success=status.get("success", False),
                    detail=status.get("detail", ""),
                )

                if use_real_scraper and not status.get("success") and status.get("detail"):
                    st.warning(f"{company['name']}: {status.get('detail')}")

                progress_status.text("Persisting scanned jobs to database...")
                progress_bar.progress(90)
                if not jobs:
                    progress_bar.progress(100)
                    progress_status.text(f"Completed scan for {selected_company} with 0 valid jobs.")
                    st.warning("No valid job-detail pages found. Existing results were kept unchanged.")
                else:
                    session = get_db_session()
                    session.query(JobMetric).delete(synchronize_session=False)
                    session.query(Job).delete(synchronize_session=False)
                    session.commit()
                    session.close()
                    inserted, updated = persist_jobs(jobs, selected_profiles=selected_profiles)
                    progress_bar.progress(100)
                    progress_status.text(f"Completed scan for {selected_company}.")
                    st.success(f"✅ {selected_company} scan complete: {len(jobs)} jobs ({inserted} new, {updated} updated).")

    with scan_col2:
        st.markdown("**Scan All Active Companies**")
        if st.button("🔍 Scan All Active Companies", use_container_width=True, key="gs_scan_all"):
            progress_bar = st.progress(0)
            progress_status = st.empty()

            total_companies = len(active_companies)
            jobs = []
            progress_status.text(f"Running scan for {total_companies} active companies...")
            for idx, company in enumerate(active_companies, start=1):
                progress_status.text(f"Scanning {idx}/{total_companies}: {company['name']}")
                company_jobs, status = scan_company_jobs(company, use_real_scraper, max_jobs, max_concurrency)
                jobs.extend(company_jobs)
                record_source_validation(
                    company,
                    mode=status.get("mode", "real" if use_real_scraper else "mock"),
                    jobs_count=len(company_jobs),
                    success=status.get("success", False),
                    detail=status.get("detail", ""),
                )
                progress_bar.progress(min(90, int((idx / max(1, total_companies)) * 80) + 10))

            progress_status.text("Persisting scanned jobs to database...")
            progress_bar.progress(92)
            if not jobs:
                progress_bar.progress(100)
                progress_status.text(f"Completed {total_companies}/{total_companies} companies with 0 valid jobs.")
                st.warning("No valid job-detail pages found. Existing results were kept unchanged.")
            else:
                session = get_db_session()
                session.query(JobMetric).delete(synchronize_session=False)
                session.query(Job).delete(synchronize_session=False)
                session.commit()
                session.close()
                inserted, updated = persist_jobs(jobs, selected_profiles=selected_profiles)
                progress_bar.progress(100)
                progress_status.text(f"Completed {total_companies}/{total_companies} companies.")
                st.success(f"✅ Scan complete: {len(jobs)} jobs processed ({inserted} new, {updated} updated).")

    st.markdown("---")
    page_dashboard(show_title=False, show_back_button=False)

def page_dashboard(show_title=True, show_back_button=True):
    """Dashboard with job cards and filters."""
    if show_title:
        st.title("💼 Dashboard")

    if show_back_button:
        if st.button("← Back to Home", key="dashboard_back_home"):
            st.session_state.page = "Get Started"
            st.rerun()
    
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

    export_col1, export_col2 = st.columns(2)
    csv_bytes = export_jobs_csv_bytes(filtered_jobs)
    export_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    with export_col1:
        st.download_button(
            "⬇️ Export CSV",
            data=csv_bytes,
            file_name=f"jobforge_jobs_{export_timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=not filtered_jobs
        )
    with export_col2:
        if HAS_PDF_EXPORT:
            pdf_bytes = export_jobs_pdf_bytes(filtered_jobs)
            st.download_button(
                "⬇️ Export PDF",
                data=pdf_bytes,
                file_name=f"jobforge_jobs_{export_timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
                disabled=not filtered_jobs
            )
        else:
            st.button("⬇️ Export PDF", disabled=True, use_container_width=True)

    if settings.get("alerts_enabled"):
        min_score = int(settings.get("alert_min_score", 80))
        max_items = int(settings.get("alert_max_items", 10))
        pending_alerts = get_new_alert_jobs(min_score=min_score, max_items=max_items)
        st.caption(f"🔔 Job Alerts: {len(pending_alerts)} unseen matches at score ≥ {min_score}")
    
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
                        set_job_saved(job["id"], True)
                        st.success("✅ Saved! See Saved Jobs page.")
                        st.rerun()
                with action_col3:
                    if st.button("❌ Remove", key=f"reject_{job['id']}", use_container_width=True):
                        removed = delete_job_by_id(job["id"])
                        if removed:
                            st.success(f"Removed {job['title']}")
                            st.rerun()
                        else:
                            st.warning("Job not found.")


def page_saved_jobs():
    """View and manage saved jobs."""
    st.title("⭐ Saved Jobs")

    if st.button("← Back to Home", key="saved_jobs_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()

    jobs = [job for job in load_jobs_from_db() if bool(job.get("saved"))]
    jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    st.caption(f"Saved jobs: {len(jobs)}")
    if not jobs:
        st.info("No saved jobs yet. Save jobs from Dashboard.")
        return

    for job in jobs:
        salary_display = get_salary_range_display(job.get("salary_min"), job.get("salary_max"))
        with st.container(border=True):
            left, right = st.columns([0.78, 0.22])
            with left:
                st.markdown(f"### {job.get('title', 'Job')}")
                st.caption(f"{job.get('company', 'Company')} • {job.get('location', 'Unknown')} • 💵 {salary_display}")
            with right:
                st.metric("Match", f"{float(job.get('match_score', 0)):.0f}%")

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if job.get("link") and job.get("link") != "manual-entry":
                    st.link_button("🔗 Open", job["link"], use_container_width=True)
                else:
                    st.button("🔗 Open", disabled=True, use_container_width=True, key=f"saved_open_disabled_{job['id']}")
            with action_col2:
                if st.button("🗑️ Delete", key=f"saved_delete_{job['id']}", use_container_width=True):
                    removed = delete_job_by_id(job["id"])
                    if removed:
                        st.success(f"Deleted {job.get('title', 'job')}")
                        st.rerun()
                    else:
                        st.warning("Job not found.")


def page_source_validation():
    """Show validation status per company source."""
    st.title("✅ Source Validation")

    if st.button("← Back to Home", key="source_validation_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()

    records = load_source_validation()
    if not records:
        st.info("No validation records yet. Run scans from Home to populate this page.")
        return

    rows = []
    for _, entry in records.items():
        rows.append(
            {
                "Company": entry.get("company", "Unknown"),
                "Mode": entry.get("mode", "-"),
                "Status": "Success" if entry.get("success") else "Failed",
                "Jobs": int(entry.get("jobs_count", 0)),
                "Checked At": entry.get("checked_at", "-"),
                "Detail": entry.get("detail", ""),
                "URL": entry.get("url", ""),
            }
        )

    rows.sort(key=lambda item: item.get("Checked At", ""), reverse=True)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def page_profile():
    """Profile setup page"""
    st.title("👤 Your Profile")

    if st.button("← Back to Home", key="profile_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()
    
    profiles = list_profiles()
    if not profiles:
        _ = get_user_profile()
        profiles = list_profiles()

    profile_map = {f"{p['name']} (ID {p['id']})": p for p in profiles}
    profile_labels = list(profile_map.keys())

    active_id = st.session_state.get("active_profile_id")
    default_index = 0
    for idx, p in enumerate(profiles):
        if p.get("id") == active_id:
            default_index = idx
            break

    select_col, create_col = st.columns([0.75, 0.25])
    with select_col:
        selected_label = st.selectbox("Select Profile", profile_labels, index=default_index)
    with create_col:
        if st.button("➕ New Profile", use_container_width=True, key="create_new_profile"):
            save_profile(
                {
                    "name": f"Profile {len(profiles) + 1}",
                    "title": "Professional",
                    "years_exp": 0,
                    "skills": [],
                    "summary": "",
                    "education": [],
                },
                profile_id=None,
            )
            st.success("Created new profile.")
            st.rerun()

    profile = profile_map[selected_label]
    st.session_state.active_profile_id = profile.get("id")
    
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
        save_profile(profile_data, profile_id=profile.get("id"))
        st.success("✅ Profile saved!")


def page_companies():
    """Manage preferred companies"""
    st.title("🏢 Preferred Companies")

    if st.button("← Back to Home", key="companies_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()

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
        st.markdown("**How this page works**")
        st.caption("Use the table below to activate/deactivate companies and delete rows directly.")
        st.caption("Only active companies are used during scans.")

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

    filtered_companies = companies

    if not filtered_companies:
        st.info("No companies match the current location filter.")

    st.markdown("---")
    st.subheader("📋 Companies")

    if filtered_companies:
        header_cols = st.columns([2.2, 1.4, 1.0, 2.7, 1.0, 1.2, 1.0])
        header_cols[0].markdown("**Company**")
        header_cols[1].markdown("**Industry**")
        header_cols[2].markdown("**State**")
        header_cols[3].markdown("**Careers URL**")
        header_cols[4].markdown("**Status**")
        header_cols[5].markdown("**Activate**")
        header_cols[6].markdown("**Delete**")

        for company in filtered_companies:
            active = bool(company.get("active", True))
            row_cols = st.columns([2.2, 1.4, 1.0, 2.7, 1.0, 1.2, 1.0])
            row_cols[0].markdown(f"{company.get('logo', '🏢')} {company.get('name', 'Unknown')}")
            row_cols[1].write(company.get("industry", "-"))
            row_cols[2].write(company.get("state", "-"))

            careers_url = normalize_url(company.get("careers_url", ""))
            if careers_url:
                row_cols[3].markdown(f"[Open]({careers_url})")
            else:
                row_cols[3].write("-")

            if active:
                row_cols[4].markdown("<span style='color:#16a34a; font-weight:600;'>Active</span>", unsafe_allow_html=True)
            else:
                row_cols[4].markdown("<span style='color:#dc2626; font-weight:600;'>Inactive</span>", unsafe_allow_html=True)

            toggle_label = "Deactivate" if active else "Activate"
            if row_cols[5].button(toggle_label, key=f"toggle_company_{company.get('id', company.get('name'))}"):
                updated_companies = []
                for current in companies:
                    if current.get("id") == company.get("id"):
                        updated = dict(current)
                        updated["active"] = not active
                        updated_companies.append(updated)
                    else:
                        updated_companies.append(current)
                save_companies(companies_path, updated_companies)
                st.rerun()

            if row_cols[6].button("Delete", key=f"delete_company_{company.get('id', company.get('name'))}"):
                updated_companies = [c for c in companies if c.get("id") != company.get("id")]
                save_companies(companies_path, updated_companies)
                st.success(f"Deleted {company.get('name', 'company')}.")
                st.rerun()

    st.markdown("---")
    st.info("Scanning is now available on the Get Started page under 'Scan Active Companies for Matching Jobs'.")


def page_add_job():
    """Manually add a job"""
    st.title("➕ Add Job Manually")

    if st.button("← Back to Home", key="add_job_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()
    
    tab1, tab2 = st.tabs(["Paste URL", "Paste Job Description"])
    
    with tab1:
        st.subheader("Paste Job URL")
        url = st.text_input("Job URL")
        use_real_scraper = is_real_scrape_mode()
        st.caption(
            "Real Scraper Mode (from sidebar): ON"
            if use_real_scraper
            else "Real Scraper Mode (from sidebar): OFF (mock generation enabled)"
        )
        
        if url and st.button("🔍 Scrape from URL"):
            st.info("🔄 Scraping job from URL...")
            job = None

            if use_real_scraper:
                if not HAS_REAL_SCRAPER:
                    st.error("Real scraper mode is ON, but Playwright scraper is unavailable.")
                else:
                    try:
                        job = run_async_task(scrape_single_job_real_async(url))
                    except Exception as e:
                        st.error(f"Real scraper failed in strict real mode. Reason: {str(e)[:120]}")
            else:
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

    if st.button("← Back to Home", key="settings_back_home"):
        st.session_state.page = "Get Started"
        st.rerun()
    
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

    st.subheader("🔔 Job Alerts")
    alerts_enabled = st.checkbox("Enable job alerts", value=bool(settings.get("alerts_enabled", False)))
    alert_col1, alert_col2 = st.columns(2)
    with alert_col1:
        alert_min_score = st.slider("Alert min match score", 50, 100, int(settings.get("alert_min_score", 80)))
    with alert_col2:
        alert_max_items = st.slider("Max jobs per alert", 1, 25, int(settings.get("alert_max_items", 10)))

    st.markdown("**Email Delivery (optional)**")
    email_col1, email_col2 = st.columns(2)
    with email_col1:
        smtp_host = st.text_input("SMTP Host", value=settings.get("smtp_host", ""))
        smtp_port = st.number_input("SMTP Port", value=int(settings.get("smtp_port", 587)), step=1)
        smtp_user = st.text_input("SMTP User", value=settings.get("smtp_user", ""))
    with email_col2:
        smtp_password = st.text_input("SMTP Password", value=settings.get("smtp_password", ""), type="password")
        alert_email_from = st.text_input("Alert From Email", value=settings.get("alert_email_from", ""))
        alert_email_to = st.text_input("Alert To Email", value=settings.get("alert_email_to", ""))

    if st.button("🔎 Check Alerts Now", use_container_width=True, disabled=not alerts_enabled):
        pending_jobs = get_new_alert_jobs(min_score=alert_min_score, max_items=alert_max_items)
        if not pending_jobs:
            st.info("No new jobs matched alert criteria.")
        else:
            st.success(f"Found {len(pending_jobs)} new alert-worthy jobs.")
            preview_limit = min(5, len(pending_jobs))
            for job in pending_jobs[:preview_limit]:
                st.caption(
                    f"• {job.get('title')} @ {job.get('company')} | "
                    f"Match {float(job.get('match_score', 0)):.0f}%"
                )

            temp_settings = {
                "smtp_host": smtp_host,
                "smtp_port": int(smtp_port),
                "smtp_user": smtp_user,
                "smtp_password": smtp_password,
                "alert_email_from": alert_email_from,
                "alert_email_to": alert_email_to,
            }
            email_sent, email_message = send_job_alert_email(pending_jobs, temp_settings)
            if email_sent:
                st.success(email_message)
            else:
                st.caption(email_message)

            mark_alert_jobs_seen(pending_jobs)

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
        st.session_state.settings_override = {
            "location": location,
            "min_salary": int(min_salary),
            "exp_level": exp_level,
            "blacklist": [item.strip() for item in blacklist.split("\n") if item.strip()],
            "alerts_enabled": bool(alerts_enabled),
            "alert_min_score": int(alert_min_score),
            "alert_max_items": int(alert_max_items),
            "smtp_host": smtp_host.strip(),
            "smtp_port": int(smtp_port),
            "smtp_user": smtp_user.strip(),
            "smtp_password": smtp_password,
            "alert_email_from": alert_email_from.strip(),
            "alert_email_to": alert_email_to.strip(),
        }

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

        st.subheader("🧪 Data Mode")
        requested_mode = st.toggle(
            "Real Scraper Mode",
            key="scrape_mode_request",
            help="ON: strict real scraping only, no mock fallback. OFF: mock data generation mode."
        )

        current_mode = bool(st.session_state.get("scrape_mode_real", False))

        if not requested_mode:
            st.session_state.suppress_real_mode_prompt = False

        if st.session_state.get("pending_real_mode", False):
            st.warning("Switching to Real mode can remove mock jobs from your database.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("✅ Confirm", use_container_width=True, key="confirm_real_mode_switch"):
                    removed = remove_mock_jobs_from_db()
                    st.session_state.scrape_mode_real = True
                    st.session_state.pending_real_mode = False
                    st.session_state.suppress_real_mode_prompt = False
                    st.success(f"Real mode enabled. Removed {removed} mock jobs from the database.")
                    st.rerun()
            with confirm_col2:
                if st.button("❌ Cancel", use_container_width=True, key="cancel_real_mode_switch"):
                    st.session_state.scrape_mode_real = False
                    st.session_state.pending_real_mode = False
                    st.session_state.suppress_real_mode_prompt = True
                    st.info("Stayed in mock mode.")
                    st.rerun()
        else:
            if requested_mode != current_mode:
                if requested_mode:
                    if not st.session_state.get("suppress_real_mode_prompt", False):
                        st.session_state.pending_real_mode = True
                        st.rerun()
                else:
                    st.session_state.scrape_mode_real = False
                    st.session_state.suppress_real_mode_prompt = False
                    st.info("Switched to mock mode.")
                    st.rerun()

        current_mode = bool(st.session_state.get("scrape_mode_real", False))
        st.caption("Mode: Real-only" if current_mode else "Mode: Mock-only")

        st.markdown("---")
        
        # Navigation menu (primary workflow)
        primary_nav_items = [
            ("Get Started", "🏠 Home"),
            ("Profile", "👤 Profile"),
            ("Preferred Companies", "🏢 Preferred Companies"),
            ("Saved Jobs", "⭐ Saved Jobs"),
        ]

        secondary_nav_items = [
            ("Settings", "⚙️ Settings"),
            ("Add Job", "➕ Manual Add"),
            ("Source Validation", "✅ Source Validation"),
        ]

        nav_items = primary_nav_items + secondary_nav_items

        if st.session_state.page not in [item[0] for item in nav_items]:
            st.session_state.page = "Get Started"

        st.caption("Main Workflow")
        for page_key, page_label in primary_nav_items:
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
        st.caption("Other Tools")
        for page_key, page_label in secondary_nav_items:
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
            4. **Scan + Browse Jobs** → Home page
            5. **Open Jobs** → Use original job links
            
            Made with ❤️ for tech job seekers.
            """)
    
    # Main content
    if st.session_state.page == "Get Started":
        page_get_started()
    elif st.session_state.page == "Profile":
        page_profile()
    elif st.session_state.page == "Preferred Companies":
        page_companies()
    elif st.session_state.page == "Saved Jobs":
        page_saved_jobs()
    elif st.session_state.page == "Source Validation":
        page_source_validation()
    elif st.session_state.page == "Add Job":
        page_add_job()
    elif st.session_state.page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
