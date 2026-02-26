#!/usr/bin/env python3
"""
JobForge Phase 0 - Quick Start Script
Run this to verify everything is installed and ready.
"""

import os
import sys
import subprocess

def check_structure():
    """Verify project structure"""
    required_files = [
        "app.py",
        "requirements.txt",
        "README.md",
        ".env.example",
        "data/companies.json",
        "utils/__init__.py",
        "utils/db.py",
        "utils/resume_parser.py",
        "utils/scraper.py",
        "utils/matching.py",
        ".streamlit/secrets.toml"
    ]
    
    print("📁 Checking project structure...")
    all_exist = True
    for file in required_files:
        path = os.path.join(os.path.dirname(__file__), file)
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file}")
        if not exists:
            all_exist = False
    
    return all_exist

def check_python():
    """Check Python version"""
    print("\n🐍 Checking Python...")
    if sys.version_info >= (3, 8):
        print(f"  ✅ Python {sys.version_info.major}.{sys.version_info.minor}")
        return True
    else:
        print(f"  ❌ Python 3.8+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
        return False

def check_dependencies():
    """Check key dependencies"""
    print("\n📦 Checking dependencies...")
    
    dependencies = [
        ("streamlit", "Streamlit"),
        ("sqlalchemy", "SQLAlchemy"),
        ("pandas", "Pandas"),
    ]
    
    all_installed = True
    for package, name in dependencies:
        try:
            __import__(package)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - run: pip install -r requirements.txt")
            all_installed = False
    
    return all_installed

def main():
    """Main check"""
    print("=" * 60)
    print("🚀 JobForge Phase 0 - Quick Start Verification")
    print("=" * 60)
    
    structure_ok = check_structure()
    python_ok = check_python()
    deps_ok = check_dependencies()
    
    print("\n" + "=" * 60)
    
    if structure_ok and python_ok and deps_ok:
        print("✅ All checks passed! Ready to run JobForge!\n")
        print("📝 Next steps:")
        print("  1. cd jobforge")
        print("  2. python -m venv venv")
        print("  3. source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
        print("  4. pip install -r requirements.txt")
        print("  5. streamlit run app.py")
        print("\n🌐 Then open: http://localhost:8501")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.\n")
        print("📝 Installation guide:")
        print("  https://github.com/yourusername/jobforge/blob/main/README.md")
        return 1

if __name__ == "__main__":
    sys.exit(main())
