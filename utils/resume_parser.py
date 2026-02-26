"""
Resume parser module for JobForge.
Extracts skills, experience, education from resume PDFs or DOCX files.
"""

import json
import re
from typing import Dict, List, Optional
import io

# Try to import PDF libraries
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from docx import Document
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

# Common tech skills for matching
TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "go", "rust", "cpp", "c++", "c#", "csharp",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash", "shell",
    # Web
    "react", "vue.js", "vue", "angular", "svelte", "nextjs", "next.js", "gatsby", "nuxt",
    "html", "css", "tailwind", "bootstrap", "django", "flask", "fastapi", "express", "node.js",
    # Cloud & DevOps
    "aws", "azure", "gcp", "kubernetes", "k8s", "docker", "terraform", "ansible", "jenkins",
    "github actions", "gitlab ci", "circleci", "terraform", "helm", "prometheus", "grafana",
    # Databases
    "postgresql", "mysql", "mongodb", "dynamodb", "redis", "elasticsearch", "cassandra", "mysql",
    # AI/ML
    "pytorch", "tensorflow", "scikit-learn", "sklearn", "huggingface", "transformers", "pandas",
    "numpy", "scikit-learn", "keras", "openai", "llm", "machine learning", "deep learning",
    # Other tools
    "git", "vim", "vscode", "jira", "confluence", "slack", "figma", "postman", "swagger",
    "grpc", "rest", "graphql", "rabbitmq", "kafka", "etcd", "vault"
}

EDUCATION_KEYWORDS = ["bachelor", "master", "phd", "diploma", "certificate", "b.s.", "m.s.", "b.a.", "m.a."]
EXPERIENCE_KEYWORDS = ["year", "month", "years experience", "exp", "yoe"]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file bytes"""
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            print(f"pdfplumber error: {e}")
    
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            print(f"PyMuPDF error: {e}")
    
    return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file bytes"""
    if not HAS_PYTHON_DOCX:
        return ""
    
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"python-docx error: {e}")
        return ""


def extract_skills(text: str) -> List[str]:
    """Extract tech skills from resume text"""
    text_lower = text.lower()
    found_skills = set()
    
    for skill in TECH_SKILLS:
        if skill in text_lower:
            found_skills.add(skill)
    
    return sorted(list(found_skills))


def extract_years_experience(text: str) -> int:
    """Try to extract years of experience"""
    patterns = [
        r'(\d+)\s*(?:\+)?\s*years?\s+(?:of\s+)?experience',
        r'(?:experience|exp)[:\s]+(\d+)\s*(?:\+)?\s*years?',
        r'(\d+)\s*(?:\+)?\s*years?\s+professional',
    ]
    
    text_lower = text.lower()
    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            try:
                return int(matches[0])
            except:
                pass
    
    return 0


def extract_current_title(text: str) -> str:
    """Extract current job title - looks for common patterns"""
    patterns = [
        r'(?:current\s+)?(?:title|position)[:\s]+([^\n]+)',
        r'^([A-Z][a-z]+\s+(?:Engineer|Manager|Developer|Architect|Lead|Director|VP)[^\n]*)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        if matches:
            return matches[0].strip()
    
    return ""


def extract_education(text: str) -> List[str]:
    """Extract education information"""
    education = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in EDUCATION_KEYWORDS):
            education.append(line.strip())
    
    return education[:3]  # Return max 3 education items


def parse_resume(file_bytes: bytes, filename: str, use_openai: bool = False) -> Dict:
    """
    Parse resume file and extract information.
    
    Args:
        file_bytes: Resume file content
        filename: Original filename
        use_openai: Whether to use OpenAI for parsing (not implemented in Phase 0)
    
    Returns:
        Dictionary with extracted resume data
    """
    # Determine file type and extract text
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif filename.lower().endswith(('.docx', '.doc')):
        text = extract_text_from_docx(file_bytes)
    else:
        text = file_bytes.decode('utf-8', errors='ignore')
    
    if not text.strip():
        return {
            "skills": [],
            "years_experience": 0,
            "current_title": "",
            "education": [],
            "summary": f"Resume parsed from {filename}",
            "raw_text": "",
            "success": False
        }
    
    # Extract components
    skills = extract_skills(text)
    years_exp = extract_years_experience(text)
    title = extract_current_title(text)
    education = extract_education(text)
    
    return {
        "skills": skills,
        "years_experience": years_exp,
        "current_title": title or "Professional",
        "education": education,
        "summary": f"Parsed resume: {len(skills)} skills found, {years_exp} years experience",
        "raw_text": text[:2000],  # Store first 2000 chars
        "success": True
    }


def mock_parse_resume(use_openai: bool = False) -> Dict:
    """Return mock resume data for demo/testing"""
    mock_data = {
        "skills": ["python", "react", "typescript", "aws", "kubernetes", "postgresql", "pytorch"],
        "years_experience": 5,
        "current_title": "Senior Full Stack Engineer",
        "education": [
            "Bachelor of Science in Computer Science - UC Berkeley",
            "Master of Science in Machine Learning - Carnegie Mellon University"
        ],
        "summary": "Full-stack engineer with 5+ years building scalable web applications and ML systems.",
        "raw_text": "Senior Full Stack Engineer...",
        "success": True,
        "is_mock": True
    }
    return mock_data


if __name__ == "__main__":
    # Test with demo data
    demo = mock_parse_resume()
    print(json.dumps(demo, indent=2))
