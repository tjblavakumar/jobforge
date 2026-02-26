"""
Real Web Scraper Module for JobForge Phase 1.
Uses Playwright with stealth mode for real-world job scraping.
Respects robots.txt and implements polite delays.
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse
import re

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    import requests
    from urllib.robotparser import RobotFileParser
    HAS_ROBOTS = True
except ImportError:
    HAS_ROBOTS = False


class PlaywrightScraper:
    """Real web scraper using Playwright with stealth mode"""
    
    # User-agent rotation for stealth
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Chrome/91.0.4472.124) Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (Chrome/91.0.4472.124) Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (Chrome/91.0.4472.124) Safari/537.36",
    ]
    
    def __init__(self, headless: bool = True):
        """Initialize scraper with Playwright"""
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.request_delay = (2, 4)  # Random delay between 2-4 seconds
    
    async def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt"""
        if not HAS_ROBOTS:
            return True  # Assume allowed if can't check
        
        try:
            domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            robots_url = f"{domain}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Check if robots.txt allows scraping
            allowed = rp.can_fetch("*", url)
            if not allowed:
                print(f"⚠️  robots.txt disallows scraping: {url}")
            return allowed
        except Exception as e:
            print(f"robots.txt check error: {e} - proceeding anyway")
            return True
    
    async def initialize(self):
        """Initialize browser with stealth mode"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not installed. Run: pip install playwright")
        
        playwright = await async_playwright().start()
        
        # Launch with stealth mode options
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        
        # Create context with stealth measures
        self.context = await self.browser.new_context(
            user_agent=random.choice(self.USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        
        # Patch navigator.webdriver
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
    
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def scrape_job_post(self, url: str, company_name: str = "Unknown") -> Optional[Dict]:
        """Scrape a single job posting from URL"""
        if not await self._check_robots_txt(url):
            return None
        
        try:
            page: Page = await self.context.new_page()
            
            # Add random delay
            delay = random.uniform(*self.request_delay)
            await asyncio.sleep(delay)
            
            # Navigate with timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            # Extract text content
            html_content = await page.content()
            text_content = await page.evaluate("() => document.body.innerText")
            
            await page.close()
            
            # Parse job details
            job = self._parse_job_content(text_content, url, company_name)
            return job
        
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    async def scrape_careers_page(self, careers_url: str, company_name: str, 
                                  max_jobs: int = 5) -> List[Dict]:
        """Scrape jobs from a careers page (generic approach)"""
        if not await self._check_robots_txt(careers_url):
            return []
        
        try:
            page: Page = await self.context.new_page()
            
            # Add random delay
            delay = random.uniform(*self.request_delay)
            await asyncio.sleep(delay)
            
            # Navigate
            await page.goto(careers_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)
            
            # Try to find job links (generic selectors)
            job_selectors = [
                "a[href*='job']",
                "a[href*='position']",
                "a[href*='career']",
                ".job-posting",
                "[data-job-id]",
            ]
            
            job_links = []
            for selector in job_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for elem in elements[:max_jobs]:
                            href = await elem.get_attribute("href")
                            if href:
                                job_links.append(href)
                        break
                except:
                    pass
            
            await page.close()
            
            # Scrape each job link
            jobs = []
            for link in job_links[:max_jobs]:
                # Make absolute URL
                if link.startswith("/"):
                    base = f"{urlparse(careers_url).scheme}://{urlparse(careers_url).netloc}"
                    link = f"{base}{link}"
                elif not link.startswith("http"):
                    link = f"{careers_url.rstrip('/')}/{link}"
                
                try:
                    job = await self.scrape_job_post(link, company_name)
                    if job:
                        jobs.append(job)
                except:
                    pass
            
            return jobs
        
        except Exception as e:
            print(f"Error scraping careers page {careers_url}: {e}")
            return []
    
    async def scrape_multiple_companies(self, companies: List[Dict], 
                                       max_jobs_per_company: int = 3) -> List[Dict]:
        """Scrape jobs from multiple companies in parallel"""
        await self.initialize()
        
        try:
            all_jobs = []
            
            # Scrape companies sequentially with delays (to be polite)
            for company in companies:
                try:
                    print(f"🔍 Scraping {company['name']}...")
                    jobs = await self.scrape_careers_page(
                        company["careers_url"],
                        company["name"],
                        max_jobs_per_company
                    )
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"Error scraping {company['name']}: {e}")
            
            return all_jobs
        
        finally:
            await self.close()
    
    def _parse_job_content(self, text_content: str, url: str, 
                          company_name: str) -> Optional[Dict]:
        """Extract job details from scraped text"""
        lines = text_content.split('\n')
        
        # Extract title (usually first substantive line)
        title = "Job Position"
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 10 and not any(x in line.lower() for x in ['cookie', 'accept', 'javascript']):
                title = line
                break
        
        # Extract salary ranges
        salary_min, salary_max = None, None
        salary_pattern = r'\$?([\d,]+)\s*(?:k|-)\s*\$?([\d,]+)(?:k)?'
        matches = re.findall(salary_pattern, text_content, re.IGNORECASE)
        if matches:
            try:
                min_val = int(matches[0][0].replace(',', ''))
                max_val = int(matches[0][1].replace(',', ''))
                # Normalize to full numbers if 'k' notation
                if min_val < 1000:
                    min_val *= 1000
                if max_val < 1000:
                    max_val *= 1000
                salary_min, salary_max = min_val, max_val
            except:
                pass
        
        # Detect remote
        is_remote = any(keyword in text_content.lower() 
                       for keyword in ['remote', 'work from home', 'wfh', 'distributed'])
        
        # Default location
        location = "Remote" if is_remote else "Onsite"
        
        return {
            "title": title,
            "company": company_name,
            "location": location,
            "salary_min": salary_min or 80000,
            "salary_max": salary_max or 150000,
            "is_remote": is_remote,
            "link": url,
            "jd_text": text_content[:2000],  # Store first 2000 chars
            "posted_date": datetime.now(timezone.utc),
            "source": company_name,
            "scraped": True
        }


# Async runner function for sync contexts
async def scrape_companies_async(companies: List[Dict], 
                                max_jobs_per_company: int = 3) -> List[Dict]:
    """Async function to scrape multiple companies"""
    scraper = PlaywrightScraper(headless=True)
    return await scraper.scrape_multiple_companies(companies, max_jobs_per_company)


def scrape_companies(companies: List[Dict], max_jobs_per_company: int = 3) -> List[Dict]:
    """Sync wrapper for scraping (handles event loop)"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        scrape_companies_async(companies, max_jobs_per_company)
    )


if __name__ == "__main__":
    # Demo
    companies = [
        {"name": "Google", "careers_url": "https://careers.google.com/jobs/results/"},
        {"name": "Meta", "careers_url": "https://www.metacareers.com/jobsearch/"}
    ]
    
    if HAS_PLAYWRIGHT:
        jobs = scrape_companies(companies, max_jobs_per_company=2)
        print(f"✅ Scraped {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"  - {job['title']} @ {job['company']}")
    else:
        print("Playwright not installed. Run: pip install playwright")
