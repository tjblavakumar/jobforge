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
from urllib.parse import urlparse, urljoin
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

    EXCLUDE_LINK_KEYWORDS = {
        "login", "sign-in", "signin", "register", "forgot", "password", "fraud",
        "validate", "offer", "privacy", "cookie", "terms", "help", "support",
        "candidate-id", "talent-acquisition", "new-user"
    }

    POSITIVE_LINK_KEYWORDS = {
        "job", "jobs", "careers", "career", "requisition", "opening", "vacancy",
        "position", "opportunity", "apply"
    }

    AUTH_WALL_KEYWORDS = {
        "log in", "login", "sign in", "register", "forgot password",
        "recruitment fraud", "validate and accept offer", "candidate id"
    }

    CORPORATE_PAGE_KEYWORDS = {
        "what we do", "who we are", "insights", "newsroom", "investors",
        "skip to main content", "skip to footer", "contact us", "global",
        "seize the future", "shape the future", "the tcs difference",
        "our inclusive workplaces", "design-thinking philosophy"
    }

    JOB_SIGNAL_KEYWORDS = {
        "responsibilities", "requirements", "qualifications", "skills",
        "experience", "job description", "role", "position", "apply",
        "requisition", "employment", "full-time", "part-time"
    }

    TCS_MARKETING_SIGNATURES = {
        "the tcs difference",
        "our research and innovation",
        "our inclusive workplaces",
        "our design-thinking philosophy",
        "shape the future of technology",
    }

    ENTRY_CLICK_KEYWORDS = {
        "early career", "early careers", "lateral", "experienced",
        "professional", "students", "graduates", "university",
        "search jobs", "view jobs", "find jobs", "explore jobs", "all jobs",
        "see opportunities", "browse jobs", "job search"
    }
    
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

            page_title = (await page.title() or "").strip()

            # Try focused job-content selectors first to avoid nav/auth/legal noise
            focused_selectors = [
                "article",
                "main",
                "[itemprop='description']",
                "[data-automation-id='jobPostingDescription']",
                "[class*='job-description']",
                "[id*='job-description']",
                "[class*='description']",
                "section"
            ]

            text_content = ""
            for selector in focused_selectors:
                try:
                    candidate = await page.evaluate(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            return el ? (el.innerText || '').trim() : '';
                        }""",
                        selector
                    )
                    if candidate and len(candidate) > 350:
                        text_content = candidate
                        break
                except Exception:
                    pass
            
            if not text_content:
                text_content = await page.evaluate("() => (document.body && document.body.innerText) ? document.body.innerText : ''")
            
            await page.close()

            combined_text = f"{page_title}\n{text_content}".lower()
            if any(keyword in combined_text for keyword in self.AUTH_WALL_KEYWORDS):
                return None
            
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

        # Try ATS/API-native adapters first for higher quality and stable URLs.
        adapter_jobs = await self._scrape_with_platform_adapter(careers_url, company_name, max_jobs)
        if adapter_jobs:
            return adapter_jobs
        
        try:
            page: Page = await self.context.new_page()
            
            # Add random delay
            delay = random.uniform(*self.request_delay)
            await asyncio.sleep(delay)
            
            # Navigate
            await page.goto(careers_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            # Try to expand common entry pages (early careers/lateral/search jobs, etc.)
            await self._expand_job_entry_points(page)
            
            # Try to find job links (generic selectors)
            job_selectors = [
                "a[href*='job']",
                "a[href*='jobs']",
                "a[href*='position']",
                "a[href*='requisition']",
                "a[href*='career']",
                ".job-posting a[href]",
                "[class*='job'] a[href]",
                "[data-job-id]",
            ]
            
            job_links = []
            for selector in job_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for elem in elements:
                            href = await elem.get_attribute("href")
                            text = (await elem.inner_text() or "").strip()
                            if href:
                                absolute = self._to_absolute_url(careers_url, href)
                                if self._is_valid_job_link(absolute, text):
                                    job_links.append((absolute, text))
                except Exception:
                    pass
            
            await page.close()

            # Deduplicate while preserving order
            deduped_links = []
            seen = set()
            for link, text in job_links:
                key = link.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    deduped_links.append((link, text))

            scored_links = sorted(
                deduped_links,
                key=lambda item: self._job_link_score(item[0], item[1]),
                reverse=True,
            )
            
            # Scrape each job link
            jobs = []
            for link, _ in scored_links[:max_jobs * 2]:
                if len(jobs) >= max_jobs:
                    break
                
                try:
                    job = await self.scrape_job_post(link, company_name)
                    if job:
                        jobs.append(job)
                except Exception:
                    pass
            
            return jobs
        
        except Exception as e:
            print(f"Error scraping careers page {careers_url}: {e}")
            return []

    async def _scrape_with_platform_adapter(self, careers_url: str, company_name: str,
                                            max_jobs: int) -> List[Dict]:
        """Try known ATS adapters before generic scraping."""
        parsed = urlparse(careers_url)
        host = (parsed.netloc or "").lower()

        if "lever.co" in host:
            return await asyncio.to_thread(self._scrape_lever_api, careers_url, company_name, max_jobs)

        if "greenhouse.io" in host:
            return await asyncio.to_thread(self._scrape_greenhouse_api, careers_url, company_name, max_jobs)

        if "workday" in host or "myworkdayjobs.com" in host or "myworkday.com" in host:
            return await self._scrape_workday_jobs(careers_url, company_name, max_jobs)

        if "successfactors" in host:
            return await self._scrape_successfactors_jobs(careers_url, company_name, max_jobs)

        major_enterprise_hosts = {
            "tcs.com",
            "infosys.com",
            "accenture.com",
            "wellsfargo.com",
            "bankofamerica.com",
            "bofa.com",
        }
        if any(domain in host for domain in major_enterprise_hosts):
            return await self._scrape_enterprise_portal_jobs(careers_url, company_name, max_jobs)

        return []

    async def _scrape_enterprise_portal_jobs(self, careers_url: str, company_name: str, max_jobs: int) -> List[Dict]:
        """Enterprise careers pages often need entry clicks + ATS outbound link discovery."""
        try:
            page: Page = await self.context.new_page()
            delay = random.uniform(*self.request_delay)
            await asyncio.sleep(delay)
            await page.goto(careers_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            await self._expand_job_entry_points(page)
            candidate_links = await self._extract_candidate_links_from_page(page, careers_url, max_jobs=max_jobs * 6)

            # Add ATS outbound links discovered in all anchors
            all_anchor_links = await page.evaluate(
                """() => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    href: a.getAttribute('href') || '',
                    text: (a.innerText || '').trim()
                }))"""
            )
            await page.close()

            ats_hosts = (
                "myworkdayjobs.com", "workday", "greenhouse.io", "lever.co",
                "successfactors", "icims", "smartrecruiters", "taleo", "brassring"
            )
            for item in all_anchor_links or []:
                href = self._to_absolute_url(careers_url, (item or {}).get("href", ""))
                text = (item or {}).get("text", "")
                lowered = href.lower()
                if any(token in lowered for token in ats_hosts) and self._is_valid_job_link(href, text):
                    candidate_links.append((href, text))

            # Deduplicate + rank
            deduped = []
            seen = set()
            for link, text in candidate_links:
                key = link.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append((link, text))

            ranked = sorted(deduped, key=lambda item: self._job_link_score(item[0], item[1]), reverse=True)

            jobs = []
            for link, _ in ranked[: max_jobs * 4]:
                if len(jobs) >= max_jobs:
                    break

                parsed = urlparse(link)
                link_host = (parsed.netloc or "").lower()

                # ATS board links: use adapter directly
                adapter_jobs = []
                if "myworkdayjobs.com" in link_host or "workday" in link_host:
                    adapter_jobs = await self._scrape_workday_jobs(link, company_name, max_jobs)
                elif "greenhouse.io" in link_host:
                    adapter_jobs = await asyncio.to_thread(self._scrape_greenhouse_api, link, company_name, max_jobs)
                elif "lever.co" in link_host:
                    adapter_jobs = await asyncio.to_thread(self._scrape_lever_api, link, company_name, max_jobs)
                elif "successfactors" in link_host:
                    adapter_jobs = await self._scrape_successfactors_jobs(link, company_name, max_jobs)

                if adapter_jobs:
                    for job in adapter_jobs:
                        if len(jobs) >= max_jobs:
                            break
                        jobs.append(job)
                    continue

                # Otherwise, try direct detail scraping
                job = await self.scrape_job_post(link, company_name)
                if job:
                    jobs.append(job)

            return jobs
        except Exception:
            return []

    async def _scrape_workday_jobs(self, careers_url: str, company_name: str, max_jobs: int) -> List[Dict]:
        """Use Workday listing endpoint discovery, then scrape detail pages for quality JD text."""
        links = await asyncio.to_thread(self._discover_workday_links, careers_url, max_jobs)
        if not links:
            return []

        jobs = []
        for link in links[: max_jobs * 2]:
            if len(jobs) >= max_jobs:
                break
            job = await self.scrape_job_post(link, company_name)
            if job:
                jobs.append(job)
        return jobs

    async def _scrape_successfactors_jobs(self, careers_url: str, company_name: str, max_jobs: int) -> List[Dict]:
        """Handle SuccessFactors-style flows by expanding entry options and collecting job-detail links."""
        try:
            page: Page = await self.context.new_page()
            delay = random.uniform(*self.request_delay)
            await asyncio.sleep(delay)
            await page.goto(careers_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            await self._expand_job_entry_points(page)
            candidate_links = await self._extract_candidate_links_from_page(page, careers_url, max_jobs=max_jobs * 3)
            await page.close()

            jobs = []
            for link, _ in candidate_links:
                if len(jobs) >= max_jobs:
                    break
                job = await self.scrape_job_post(link, company_name)
                if job:
                    jobs.append(job)
            return jobs
        except Exception:
            return []

    def _scrape_lever_api(self, careers_url: str, company_name: str, max_jobs: int) -> List[Dict]:
        """Fetch jobs from Lever public postings API."""
        if 'requests' not in globals():
            return []

        parsed = urlparse(careers_url)
        path_parts = [part for part in (parsed.path or "").split("/") if part]
        if not path_parts:
            return []

        company_slug = path_parts[0]
        api_url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

        try:
            response = requests.get(api_url, timeout=20)
            if response.status_code != 200:
                return []
            payload = response.json()
            if not isinstance(payload, list):
                return []

            jobs = []
            for item in payload[:max_jobs]:
                title = (item.get("text") or "Job Position").strip()
                link = (item.get("hostedUrl") or "").strip()
                description = (item.get("descriptionPlain") or item.get("description") or "").strip()
                if not description:
                    lists = item.get("lists") or []
                    if isinstance(lists, list):
                        chunks = []
                        for section in lists:
                            heading = section.get("text") or ""
                            content_items = section.get("content") or []
                            if heading:
                                chunks.append(str(heading))
                            for entry in content_items:
                                chunks.append(str(entry))
                        description = "\n".join(chunks)

                if not link or not description or len(description) < 120:
                    continue

                location = "Unknown"
                categories = item.get("categories") or {}
                if isinstance(categories, dict):
                    location = categories.get("location") or "Unknown"

                is_remote = "remote" in location.lower() or "remote" in description.lower()
                cleaned_description = self._clean_job_text(description)
                if len(cleaned_description) < 120:
                    continue

                jobs.append({
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "salary_min": 80000,
                    "salary_max": 150000,
                    "is_remote": is_remote,
                    "link": link,
                    "jd_text": cleaned_description[:2000],
                    "posted_date": datetime.now(timezone.utc),
                    "source": f"{company_name} Careers",
                    "scraped": True,
                    "data_mode": "real",
                })

            return jobs
        except Exception:
            return []

    def _scrape_greenhouse_api(self, careers_url: str, company_name: str, max_jobs: int) -> List[Dict]:
        """Fetch jobs from Greenhouse boards API."""
        if 'requests' not in globals():
            return []

        parsed = urlparse(careers_url)
        path_parts = [part for part in (parsed.path or "").split("/") if part]
        if not path_parts:
            return []

        board_token = path_parts[0]
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"

        try:
            response = requests.get(api_url, timeout=20)
            if response.status_code != 200:
                return []
            payload = response.json()
            entries = payload.get("jobs") if isinstance(payload, dict) else None
            if not isinstance(entries, list):
                return []

            jobs = []
            for item in entries[:max_jobs]:
                title = (item.get("title") or "Job Position").strip()
                link = (item.get("absolute_url") or "").strip()
                content = (item.get("content") or "").strip()
                # Remove basic HTML tags if content is HTML
                content_text = re.sub(r"<[^>]+>", " ", content)
                content_text = re.sub(r"\s+", " ", content_text).strip()
                if not link or not content_text or len(content_text) < 120:
                    continue

                location = "Unknown"
                loc_obj = item.get("location")
                if isinstance(loc_obj, dict):
                    location = (loc_obj.get("name") or "Unknown").strip()

                is_remote = "remote" in location.lower() or "remote" in content_text.lower()
                cleaned_description = self._clean_job_text(content_text)
                if len(cleaned_description) < 120:
                    continue

                jobs.append({
                    "title": title,
                    "company": company_name,
                    "location": location,
                    "salary_min": 80000,
                    "salary_max": 150000,
                    "is_remote": is_remote,
                    "link": link,
                    "jd_text": cleaned_description[:2000],
                    "posted_date": datetime.now(timezone.utc),
                    "source": f"{company_name} Careers",
                    "scraped": True,
                    "data_mode": "real",
                })

            return jobs
        except Exception:
            return []

    def _discover_workday_links(self, careers_url: str, max_jobs: int) -> List[str]:
        """Discover Workday job links via CXS endpoint if available."""
        if 'requests' not in globals():
            return []

        try:
            response = requests.get(careers_url, timeout=20)
            if response.status_code >= 400:
                return []
            html = response.text

            endpoint_match = re.search(r"(/wday/cxs/[^\"'\s]+/[^\"'\s]+/jobs)", html)
            if not endpoint_match:
                return []

            parsed = urlparse(careers_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            endpoint = endpoint_match.group(1)
            api_url = urljoin(origin, endpoint)

            payload = {
                "appliedFacets": {},
                "limit": max(20, max_jobs * 5),
                "offset": 0,
                "searchText": "",
            }
            headers = {"Content-Type": "application/json"}
            jobs_resp = requests.post(api_url, json=payload, headers=headers, timeout=25)
            if jobs_resp.status_code >= 400:
                return []

            data = jobs_resp.json()
            postings = data.get("jobPostings") if isinstance(data, dict) else None
            if not isinstance(postings, list):
                return []

            links = []
            for posting in postings:
                ext = (posting.get("externalPath") or "").strip()
                if not ext:
                    continue
                link = urljoin(origin, ext if ext.startswith("/") else f"/{ext}")
                links.append(link)

            # Deduplicate preserve order
            deduped = []
            seen = set()
            for link in links:
                key = link.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    deduped.append(link)

            return deduped[:max_jobs * 3]
        except Exception:
            return []

    async def _expand_job_entry_points(self, page: Page):
        """Click common entry-point buttons/links that reveal real job search pages."""
        click_selectors = [
            "a", "button", "[role='button']", "div[role='link']"
        ]
        for selector in click_selectors:
            try:
                elements = await page.query_selector_all(selector)
            except Exception:
                continue

            for element in elements[:120]:
                try:
                    text = (await element.inner_text() or "").strip().lower()
                    if not text:
                        continue
                    if not any(keyword in text for keyword in self.ENTRY_CLICK_KEYWORDS):
                        continue

                    await element.click(timeout=1500)
                    await asyncio.sleep(1)
                except Exception:
                    continue

    async def _extract_candidate_links_from_page(self, page: Page, base_url: str, max_jobs: int = 20) -> List[tuple]:
        """Extract candidate job links from an already-loaded page."""
        selectors = [
            "a[href*='job']",
            "a[href*='jobs']",
            "a[href*='position']",
            "a[href*='requisition']",
            "a[href*='career']",
            ".job-posting a[href]",
            "[class*='job'] a[href]",
            "[data-job-id] a[href]",
            "a[href*='jobReqId']",
        ]

        raw_links = []
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
            except Exception:
                continue

            for elem in elements:
                try:
                    href = await elem.get_attribute("href")
                    text = (await elem.inner_text() or "").strip()
                except Exception:
                    continue
                if not href:
                    continue
                absolute = self._to_absolute_url(base_url, href)
                if self._is_valid_job_link(absolute, text):
                    raw_links.append((absolute, text))

        deduped = []
        seen = set()
        for link, text in raw_links:
            key = link.lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append((link, text))

        ranked = sorted(deduped, key=lambda item: self._job_link_score(item[0], item[1]), reverse=True)
        return ranked[:max_jobs]
    
    async def scrape_multiple_companies(self, companies: List[Dict], 
                                       max_jobs_per_company: int = 3,
                                       max_concurrency: int = 3) -> List[Dict]:
        """Scrape jobs from multiple companies in parallel with bounded concurrency."""
        await self.initialize()
        
        try:
            all_jobs = []
            safe_concurrency = max(1, int(max_concurrency))
            semaphore = asyncio.Semaphore(safe_concurrency)

            async def scrape_one(company: Dict) -> List[Dict]:
                async with semaphore:
                    try:
                        print(f"🔍 Scraping {company['name']}...")
                        return await self.scrape_careers_page(
                            company["careers_url"],
                            company["name"],
                            max_jobs_per_company
                        )
                    except Exception as e:
                        print(f"Error scraping {company.get('name', 'Unknown')}: {e}")
                        return []

            tasks = [scrape_one(company) for company in companies]
            results = await asyncio.gather(*tasks, return_exceptions=False)
            for jobs in results:
                all_jobs.extend(jobs)

            return all_jobs
        
        finally:
            await self.close()
    
    def _parse_job_content(self, text_content: str, url: str, 
                          company_name: str) -> Optional[Dict]:
        """Extract job details from scraped text"""
        if not text_content or len(text_content.strip()) < 200:
            return None

        lowered = text_content.lower()
        if any(keyword in lowered for keyword in self.AUTH_WALL_KEYWORDS):
            return None

        text_content = self._clean_job_text(text_content)
        if not self._looks_like_real_job_page(text_content, url):
            return None

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
            "source": f"{company_name} Careers",
            "scraped": True,
            "data_mode": "real"
        }

    def _to_absolute_url(self, base_url: str, href: str) -> str:
        try:
            return urljoin(base_url, href).strip()
        except Exception:
            return href.strip()

    def _is_valid_job_link(self, link: str, anchor_text: str = "") -> bool:
        if not link or not link.startswith(("http://", "https://")):
            return False

        lowered = f"{link} {anchor_text}".lower()

        if any(word in lowered for word in self.EXCLUDE_LINK_KEYWORDS):
            return False

        strong_job_tokens = {"job", "jobs", "requisition", "position", "opening", "vacancy", "jobreqid"}
        if any(word in lowered for word in strong_job_tokens):
            return True

        if "apply" in lowered and re.search(r"[0-9]{3,}", lowered):
            return True

        # Accept URLs with likely unique job IDs
        return bool(re.search(r"(job|req|position|opening)[-_]?[0-9]{3,}", lowered))

    def _job_link_score(self, link: str, anchor_text: str = "") -> int:
        lowered = f"{link} {anchor_text}".lower()
        score = 0
        for word in self.POSITIVE_LINK_KEYWORDS:
            if word in lowered:
                score += 2
        if re.search(r"[0-9]{4,}", lowered):
            score += 2
        if "apply" in lowered:
            score += 1
        if any(word in lowered for word in self.EXCLUDE_LINK_KEYWORDS):
            score -= 6
        return score

    def _clean_job_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        cleaned = []
        for line in lines:
            lowered = line.lower()
            if not line:
                continue
            if any(keyword in lowered for keyword in self.AUTH_WALL_KEYWORDS):
                continue
            if any(token in lowered for token in ["privacy notice", "copyright ©", "new user", "forgot password"]):
                continue
            cleaned.append(line)

        collapsed = "\n".join(cleaned)
        # Keep a practical max length
        return collapsed[:5000]

    def _looks_like_real_job_page(self, text: str, url: str) -> bool:
        """Reject corporate landing pages and keep likely job descriptions only."""
        lowered = (text or "").lower()
        url_l = (url or "").lower()

        if len(lowered.strip()) < 200:
            return False

        # Corporate/marketing-heavy page guard
        corporate_hits = sum(1 for keyword in self.CORPORATE_PAGE_KEYWORDS if keyword in lowered)
        job_hits = sum(1 for keyword in self.JOB_SIGNAL_KEYWORDS if keyword in lowered)

        # Hard reject for known TCS brand/landing signatures
        tcs_hits = sum(1 for keyword in self.TCS_MARKETING_SIGNATURES if keyword in lowered)
        if tcs_hits >= 2:
            return False

        # If many corporate signals and almost no job signals, reject
        if corporate_hits >= 2 and job_hits <= 2:
            return False

        # Require at least a few job-specific indicators unless URL clearly looks like job-detail
        url_looks_job_detail = bool(re.search(r"(job|jobs|requisition|position|opening|vacancy|jobreqid)", url_l))
        if job_hits < 2 and not url_looks_job_detail:
            return False

        # Reject giant navigation pages with too few line breaks into sections
        section_like = lowered.count("requirements") + lowered.count("responsibilities") + lowered.count("qualifications")
        if section_like == 0 and job_hits < 3:
            return False

        return True


# Async runner function for sync contexts
async def scrape_companies_async(companies: List[Dict], 
                                max_jobs_per_company: int = 3,
                                max_concurrency: int = 3) -> List[Dict]:
    """Async function to scrape multiple companies"""
    scraper = PlaywrightScraper(headless=True)
    return await scraper.scrape_multiple_companies(
        companies,
        max_jobs_per_company=max_jobs_per_company,
        max_concurrency=max_concurrency
    )


def scrape_companies(companies: List[Dict], max_jobs_per_company: int = 3,
                    max_concurrency: int = 3) -> List[Dict]:
    """Sync wrapper for scraping (handles event loop)"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(
        scrape_companies_async(
            companies,
            max_jobs_per_company=max_jobs_per_company,
            max_concurrency=max_concurrency
        )
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
