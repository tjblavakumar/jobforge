# 🚀 JobForge Phase 3 - Smart Search

A clean, locally-deployable Streamlit application for managing and analyzing tech/software job opportunities. Built for privacy-first job search with offline-first design.

## ✨ Features (Phase 3)

- **📊 Dashboard**: Card-based job feed with semantic match scores (0-100%), filters, sort controls, and active filter summary
- **💾 Saved Search Presets**: Save/load/delete reusable filter + sort presets
- **👤 Profile Management**: Upload resume (PDF/DOCX) with auto-parsing, manual skill editing
- **🏢 Preferred Companies**: Built-in company list + add/delete actions, careers URL validation, California-only filter, real-scraper mode + mock fallback
- **➕ Add Jobs Manually**: Paste URLs (real scraper or mock fallback) or full job descriptions
- **⚙️ Settings**: Configure OpenAI API key and one-click OpenAI re-scoring
- **🎨 UI Refresh**: Blue theme + dark-mode-friendly styling updates
- **💾 SQLite Database**: All data stored locally, never leaves your machine
- **🌐 Offline Mode**: Works fully without OpenAI API key using local embeddings
- **📈 Progress Indicators**: Live progress/status for company scans and bulk OpenAI re-scoring

## 🏗️ Project Structure

```
jobforge/
├── app.py                 # Main Streamlit app (Phase 3 - single file)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── .streamlit/
│   └── secrets.toml      # Secrets (optional, for API keys)
├── data/
│   ├── companies.json    # Preferred companies and careers URLs
│   ├── search_presets.json # Saved dashboard presets (generated)
│   ├── jobs.db           # SQLite database (generated)
│   └── profiles.db       # User profiles database (generated)
└── utils/
    ├── db.py             # SQLAlchemy models & database operations
    ├── resume_parser.py  # Resume PDF/DOCX parsing
    ├── scraper.py        # Mock scraper fallback
    ├── real_scraper.py   # Real Playwright scraper
    ├── openai_integration.py # GPT-4o-mini analysis helpers
    └── matching.py       # Job matching & scoring engine
```

## 🚀 Quick Start

### 1. Clone/Setup

```bash
# Navigate to project
cd jobforge

# Create virtual environment (recommended)
python -m venv venv

# Activate
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Optional: If you want real PDF parsing with better quality:
```bash
# pdfplumber will try to use this automatically
# No additional steps needed - it falls back gracefully
```

### 3. Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

### 4. (Optional) Add OpenAI API Key

Create `.streamlit/secrets.toml` in the project root:

```toml
OPENAI_API_KEY = "sk-proj-..."
LOCATION = "San Francisco, CA"
MIN_SALARY = 150000
EXP_LEVEL = "senior"
```

Or use `.env`:
```bash
cp .env.example .env
# Edit .env with your settings
```

## 📖 How to Use

### 1. **Profile Setup** (👤 Your Profile)
   - Upload your resume (PDF or DOCX)
   - Auto-parsed resume extracts: skills, years of experience, title, education
   - Edit manually if needed
   - Skills display as nice chips

### 2. **Configure Preferences** (⚙️ Settings)
  - Add OpenAI API key (optional)
  - Re-score all jobs with OpenAI (optional)
  - Adjust location/salary/experience inputs as local preferences

### 3. **Add Companies** (🏢 Preferred Companies)
  - Browse pre-loaded companies with careers URLs
  - Add custom companies and delete entries directly in UI
  - Validate careers URLs before/after saving
  - Filter companies to California-only sources when needed
  - Use "Scan All" and "Scan Single" with real scraper toggle
  - View live scan/persist progress indicators

### 4. **Manage Jobs** (💼 Dashboard)
   - View all available jobs in card layout with inline actions
   - **Match Score (0-100%)**:
     - **Blue (70-100%)**: Excellent fit - high priority
     - **Indigo (50-69%)**: Good fit - worth reviewing
     - **Red (<50%)**: Lower priority
   - **Filters**:
     - 💰 Salary range slider
     - 🌍 Remote toggle
     - 🏢 Company multi-select
     - 📅 Posted within X days
   - **Sort**: Best Match, Newest, Highest Salary
   - **Saved Presets**: Save/load/delete filter and sort combinations
   - **Actions**: Open, Save, Mark as Viewed, Remove
   - **OpenAI Actions** (when API key is configured):
     - Analyze Match
     - Generate Interview Prep

### 5. **Add Jobs Manually** (➕ Add Job)
  - Paste job URL to auto-scrape with real mode + fallback
   - Or paste full job description text
   - Supports mixed input

### 6. **Re-score Existing Jobs** (⚙️ Settings)
  - One-click "Re-score All Jobs (OpenAI)"
  - Live per-job progress during rescoring

## 🧠 Match Score Algorithm

Combines multiple signals:

```
Final Score = (
    35% × Semantic Similarity (embeddings) +
    25% × Salary Alignment +
    25% × Skills Match +
    10% × Remote/Location Bonus +
    5% × OpenAI Deeper Analysis (if API key provided)
)
```

- **Semantic Similarity**: Uses `sentence-transformers/all-MiniLM-L6-v2` to compare job description to user profile
- **Salary**: Checks if job salary range overlaps with user expectations
- **Skills**: Counts keyword matches between job description and user skills
- **Location**: Bonus if remote preference matches job type
- **OpenAI**: Deeper contextual analysis with GPT-4o-mini (optional)

## 🗄️ Database

### Jobs Table

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255),
    company VARCHAR(255),
    location VARCHAR(255),
    salary_min INTEGER,
    salary_max INTEGER,
    is_remote BOOLEAN,
    link VARCHAR(1024),
    jd_text TEXT,
    posted_date DATETIME,
    source VARCHAR(100),
    created_at DATETIME
);
```

### Profile Table

```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    user_name VARCHAR(255),
    current_title VARCHAR(255),
    years_experience INTEGER,
    summary TEXT,
    skills TEXT,  -- JSON array
    education TEXT,  -- JSON array
    resume_text TEXT,
    created_at DATETIME
);
```

### Job Metrics Table

```sql
CREATE TABLE job_metrics (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    match_score FLOAT,
    semantic_score FLOAT,
    openai_score FLOAT,
    viewed BOOLEAN,
    saved BOOLEAN,
    rejected BOOLEAN,
    created_at DATETIME
);
```

## ⚙️ Configuration

### `.streamlit/secrets.toml` (Recommended)

```toml
OPENAI_API_KEY = "sk-proj-xxx"  # Optional
LOCATION = "United States"
MIN_SALARY = 100000
EXP_LEVEL = "senior"
WORK_TYPE = "remote"
BLACKLIST = "Company1,Company2"
FRESHNESS_DAYS = 30
```

### `.env` (Alternative)

```bash
OPENAI_API_KEY=sk-...
LOCATION=United States
MIN_SALARY=100000
```

## 🔐 Security & Privacy

- ✅ **All data stored locally** in SQLite (`data/jobs.db`, `data/profiles.db`)
- ✅ **Offline first**: Works completely without internet after initial setup
- ✅ **No tracking**: No analytics, no telemetry
- ✅ **Resume stays private**: Processed locally, never sent anywhere
- ✅ **Optional OpenAI**: Only used if you provide API key
- ✅ **No cloud sync**: All data stays on your machine

## 🧪 Demo Data

Phase 3 ships with ~12 realistic demo jobs pre-seeded in database:
- Senior Software Engineer @ Google
- ML Engineer @ Meta
- Full Stack Engineer @ Stripe
- Plus others from top tech companies

Delete `data/jobs.db` to reset.

## 🛣️ Roadmap - Phase 3 & Beyond

### Phase 3 (Smart Search)
- [x] **Job-search-only Simplification**: Removed application tracking and salary pages
- [x] **Dashboard Refresh**: Card-first layout with integrated actions
- [x] **Saved Search Presets**: Save/load/delete reusable filter sets
- [x] **Sort Controls**: Best Match, Newest, Highest Salary
- [x] **Company Management**: Add/delete company sources + URL validation
- [x] **Theme Refresh**: Blue color system + dark-mode improvements
- [ ] **Async Scraping**: Full parallel multi-company scraping pipeline
- [ ] **Job Alerts**: Email/push notifications for new matches
- [ ] **Export**: CSV/PDF exports

### Phase 4 (Multi-User & Cloud)
- [ ] **Cloud Warehouse**: Optional sync (encrypted)
- [ ] **Team Features**: Share job findings with friends
- [ ] **Integration**: Slack, Gmail, Google Calendar
- [ ] **Mobile App**: React Native version

## 🤝 Contributing

Want to improve JobForge? Ideas for Phase 3+:
- Better resume parsing
- Additional company data sources
- Custom matching algorithms
- UI improvements
- Bug reports

## 📝 License

MIT License - Free to use and modify.

## ❓ FAQ

**Q: Does it require internet?**
A: No! After initial setup, everything works offline. OpenAI API is optional.

**Q: Can I export my data?**
A: Yes! The SQLite database (`data/jobs.db`) can be exported or queried directly.

**Q: How accurate is the match score?**
A: It's a heuristic combination of semantic matching + keyword matching. Use it as a guide, not gospel.

**Q: Can I scrape real job boards?**
A: Yes. JobForge includes an optional real Playwright scraper mode with mock fallback. Always respect `robots.txt` and terms of service.

**Q: Is my resume really private?**
A: Yes! It's only processed locally. OpenAI is never called unless you explicitly configure it.

---

**Made with ❤️ for job seekers who care about privacy and efficiency.**

🚀 Ready to find your dream job? Start with `streamlit run app.py`!
