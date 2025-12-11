"""
WIPO Crawler v3.3 MINIMAL-DEBUG - v3.1 + Enhanced Logging
Baseline: v3.1 that WORKED for title/abstract extraction
Changes: ONLY added detailed logging to diagnose worldwide extraction
"""
import asyncio
import random
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Create screenshots dir if not exists
Path("screenshots").mkdir(exist_ok=True)

class WIPOCrawler:
    """
    PRODUCTION crawler (v3.1 baseline) with enhanced logging
    
    CHANGES from v3.1:
    - Added step-by-step logging in _extract_worldwide_applications
    - Added HTML content logging at critical points
    - NO CHANGES to selectors or validation logic
    """
    
    def __init__(self, max_retries: int = 3, timeout: int = 60000, headless: bool = True):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.screenshots_enabled = True
        
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            java_script_enabled=True
        )
        
        logger.info("✅ WIPO Crawler initialized (v3.3 MINIMAL-DEBUG)")
    
    async def close(self):
        """Clean shutdown"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _normalize_wo(self, wo: str) -> str:
        """Normalize WO number"""
        wo = wo.upper().replace(' ', '').replace('-', '').replace('/', '')
        return wo if wo.startswith('WO') else 'WO' + wo
    
    async def _take_screenshot(self, page: Page, name: str):
        """Take debug screenshot"""
        if not self.screenshots_enabled:
            return
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshots/{name}_{timestamp}.png"
            await page.screenshot(path=filename, full_page=True)
            logger.debug(f"📸 Screenshot: {filename}")
        except Exception as e:
            logger.debug(f"Screenshot failed: {e}")
    
    async def _extract_title(self, page: Page) -> Tuple[Optional[str], str]:
        """Extract title with fallback selectors"""
        selectors = [
            'h3.tab_title',
            'div.title',
            'h1',
            'h2',
            'span.patent-title',
            'div[class*="title"]'
        ]
        
        for sel in selectors:
            try:
                elems = await page.query_selector_all(sel)
                for elem in elems:
                    text = (await elem.inner_text()).strip()
                    if text and len(text) > 20 and len(text) < 500:
                        logger.info(f"    ✅ Title: {sel}")
                        return text, sel
            except:
                continue
        
        logger.warning("    ⚠️ NO title found")
        return None, 'none'
    
    async def _extract_abstract(self, page: Page) -> Tuple[Optional[str], str]:
        """Extract abstract"""
        selectors = [
            'div.abstract',
            'div#abstract',
            'p.abstract',
            'section.abstract',
            'div[class*="bstract"]'
        ]
        
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    text = (await elem.inner_text()).strip()
                    if text and len(text) > 50:
                        logger.info(f"    ✅ Abstract: {sel}")
                        return text[:1000], sel
            except:
                continue
        
        logger.warning("    ⚠️ NO abstract found")
        return None, 'none'
    
    async def _extract_applicant(self, page: Page) -> Tuple[Optional[str], str]:
        """Extract applicant/titular"""
        try:
            rows = await page.query_selector_all('tr')
            for row in rows:
                row_text = (await row.inner_text()).lower()
                
                if 'applicant' in row_text or 'titular' in row_text:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 2:
                        text = (await cells[1].inner_text()).strip()
                        text = re.sub(r'\[.*?\]', '', text).strip()
                        text = text.split('\n')[0].strip()
                        
                        if text and len(text) > 3:
                            logger.info(f"    ✅ Applicant: table row")
                            return text, 'table_row'
        except:
            pass
        
        logger.warning("    ⚠️ NO applicant found")
        return None, 'none'
    
    async def _extract_dates(self, page: Page) -> Tuple[Dict, List[str]]:
        """Extract filing, publication, priority dates"""
        dates = {'deposito': None, 'publicacao': None, 'prioridade': None}
        found = []
        
        try:
            rows = await page.query_selector_all('tr')
            
            keywords = {
                'deposito': ['filing date', 'application date'],
                'publicacao': ['publication date', 'international publication'],
                'prioridade': ['priority date']
            }
            
            for date_type, kws in keywords.items():
                for row in rows:
                    row_text = (await row.inner_text()).lower()
                    
                    if any(kw in row_text for kw in kws):
                        cells = await row.query_selector_all('td')
                        if len(cells) >= 2:
                            date_text = (await cells[1].inner_text()).strip()
                            date_match = re.search(r'(\d{2}[./]\d{2}[./]\d{4})|(\d{4}[-/]\d{2}[-/]\d{2})', date_text)
                            
                            if date_match:
                                dates[date_type] = date_match.group(0)[:10]
                                found.append(date_type)
                                break
        except:
            pass
        
        if found:
            logger.info(f"    ✅ Dates: {', '.join(found)}")
        else:
            logger.warning("    ⚠️ NO dates found")
        
        return dates, found
    
    async def _extract_worldwide_applications(self, page: Page) -> Tuple[Dict, int, List[str]]:
        """
        Extract worldwide applications - v3.1 logic + ENHANCED LOGGING
        """
        worldwide = {}
        total_apps = 0
        debug_info = []
        
        logger.info("  🌍 Extracting worldwide applications...")
        logger.info("  📝 STEP 1: Looking for National Phase tab...")
        
        # Step 1: Click tab
        tab_selectors = [
            'a:has-text("National Phase")',
            'button:has-text("National Phase")',
            'div:has-text("National Phase")',
            '#national-phase-tab',
            'a[href*="national"]'
        ]
        
        clicked = False
        for sel in tab_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    logger.info(f"    🎯 Found tab element: {sel}")
                    await elem.click()
                    logger.info(f"    ✅ Clicked: {sel}")
                    debug_info.append(f"clicked:{sel}")
                    clicked = True
                    break
            except Exception as e:
                logger.debug(f"    ❌ Tab click failed ({sel}): {e}")
                continue
        
        if not clicked:
            logger.warning("    ⚠️ Could NOT click National Phase tab")
            debug_info.append("click_failed")
            return worldwide, 0, debug_info
        
        # Step 2: WAIT for content
        logger.info("  📝 STEP 2: Waiting 4 seconds for AJAX load...")
        await page.wait_for_timeout(4000)
        
        # Take screenshot after wait
        await self._take_screenshot(page, "after_national_phase_click")
        
        # Step 3: Look for table
        logger.info("  📝 STEP 3: Searching for table...")
        
        table_selectors = [
            'table.national-phase-table tr',
            'div.national-phase table tr',
            'table#national-phase tr',
            'table tr'  # Fallback
        ]
        
        rows_found = []
        
        for table_sel in table_selectors:
            try:
                rows = await page.query_selector_all(table_sel)
                
                if len(rows) > 1:
                    logger.info(f"    ✅ Table found: {table_sel} ({len(rows)} rows)")
                    debug_info.append(f"table:{table_sel}:{len(rows)}")
                    rows_found = rows
                    break
                else:
                    logger.debug(f"    ⚠️ Selector '{table_sel}' found {len(rows)} rows (too few)")
            except Exception as e:
                logger.debug(f"    ❌ Selector '{table_sel}' failed: {e}")
                continue
        
        if not rows_found or len(rows_found) <= 1:
            logger.warning("    ❌ NO table data found after trying all selectors")
            debug_info.append("no_table_data")
            
            # DEBUG: Log page content
            try:
                content = await page.content()
                logger.debug(f"    📄 Page HTML length: {len(content)} chars")
                if 'national' in content.lower():
                    logger.debug("    ✅ Word 'national' found in HTML")
                else:
                    logger.debug("    ⚠️ Word 'national' NOT found in HTML")
            except:
                pass
            
            return worldwide, 0, debug_info
        
        # Step 4: Parse rows
        logger.info(f"  📝 STEP 4: Parsing {len(rows_found)-1} rows...")
        
        for idx, row in enumerate(rows_found[1:], 1):  # Skip header
            try:
                cells = await row.query_selector_all('td')
                
                if len(cells) < 2:
                    continue
                
                # Extract texts
                cell_texts = []
                for cell in cells[:6]:
                    try:
                        text = (await cell.inner_text()).strip()
                        cell_texts.append(text)
                    except:
                        cell_texts.append('')
                
                # Parse columns
                filing_date = ''
                country = ''
                app_num = ''
                status = ''
                
                for text in cell_texts:
                    if not filing_date and re.match(r'\d{2}[./]\d{2}[./]\d{4}|\d{4}[-/]\d{2}[-/]\d{2}', text):
                        filing_date = text[:10]
                    elif not country and re.match(r'^[A-Z]{2,3}$', text):
                        country = text
                    elif not app_num and len(text) > 5 and any(c.isdigit() for c in text):
                        app_num = text
                    elif not status and len(text) > 3:
                        status = text
                
                if not country or len(country) > 3:
                    continue
                
                # Extract year
                year = 'unknown'
                if filing_date:
                    year_match = re.search(r'(\d{4})', filing_date)
                    if year_match:
                        year = year_match.group(1)
                
                # Add to worldwide
                if year not in worldwide:
                    worldwide[year] = []
                
                worldwide[year].append({
                    'filing_date': filing_date,
                    'country_code': country,
                    'application_number': app_num,
                    'legal_status': status
                })
                
                total_apps += 1
                
                if idx <= 3:
                    logger.debug(f"      Row {idx}: {country} | {filing_date} | {app_num}")
            
            except Exception as e:
                logger.debug(f"    Row parse error {idx}: {e}")
                continue
        
        logger.info(f"  📊 Worldwide: {total_apps} apps from {len(worldwide)} years")
        debug_info.append(f"extracted:{total_apps}")
        
        return worldwide, total_apps, debug_info
    
    async def fetch_patent(self, wo_number: str) -> Dict[str, Any]:
        """Fetch patent - v3.1 BASELINE (WORKED!)"""
        wo = self._normalize_wo(wo_number)
        url = f"https://patentscope.wipo.int/search/en/detail.jsf?docId={wo}"
        
        logger.info(f"🔍 Fetching {wo} (v3.3 MINIMAL-DEBUG)...")
        
        for retry in range(self.max_retries):
            try:
                logger.info(f"  🔄 Attempt {retry + 1}/{self.max_retries}")
                
                page = await self.context.new_page()
                
                # Navigate
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                await self._take_screenshot(page, f"{wo}_initial")
                
                # Extract data (v3.1 baseline methods)
                titulo, titulo_sel = await self._extract_title(page)
                resumo, resumo_sel = await self._extract_abstract(page)
                titular, titular_sel = await self._extract_applicant(page)
                datas, date_sels = await self._extract_dates(page)
                
                # Extract worldwide
                worldwide, total_apps, worldwide_debug = await self._extract_worldwide_applications(page)
                
                await self._take_screenshot(page, f"{wo}_final")
                
                await page.close()
                
                # Calculate countries
                countries = sorted(list(set(
                    app['country_code']
                    for apps in worldwide.values()
                    for app in apps
                    if app.get('country_code')
                )))
                
                # VALIDATION (v3.1 BASELINE - FLEXIBLE!)
                has_data = any([
                    titulo,
                    resumo,
                    titular,
                    any(datas.values()),
                    worldwide
                ])
                
                if not has_data:
                    raise ValueError("No data extracted from any selector")
                
                # Build result
                result = {
                    'fonte': 'WIPO',
                    'publicacao': wo,
                    'titulo': titulo,
                    'resumo': resumo,
                    'titular': titular,
                    'datas': datas,
                    'inventores': [],
                    'cpc_ipc': [],
                    'pdf_link': None,
                    'worldwide_applications': worldwide,
                    'paises_familia': countries,
                    'debug': {
                        'selectors_found': {
                            'titulo': titulo_sel,
                            'resumo': resumo_sel,
                            'titular': titular_sel,
                            'datas': date_sels
                        },
                        'worldwide': worldwide_debug,
                        'total_worldwide_apps': total_apps,
                        'countries_found': len(countries),
                        'retry_attempt': retry + 1,
                        'url': url
                    }
                }
                
                logger.info(f"✅ {wo}: SUCCESS")
                logger.info(f"   Title: {'YES' if titulo else 'NO'} ({titulo_sel})")
                logger.info(f"   Resumo: {'YES' if resumo else 'NO'} ({resumo_sel})")
                logger.info(f"   Applicant: {'YES' if titular else 'NO'} ({titular_sel})")
                logger.info(f"   Dates: {len(date_sels)}/3")
                logger.info(f"   Worldwide: {total_apps} apps, {len(countries)} countries")
                
                return result
            
            except Exception as e:
                logger.error(f"❌ Attempt {retry + 1} failed: {e}")
                
                try:
                    await page.close()
                except:
                    pass
                
                if retry < self.max_retries - 1:
                    wait_time = (2 ** retry) + random.uniform(0, 2)
                    logger.info(f"   ⏳ Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"💥 {wo}: FAILED after {self.max_retries} attempts")
                    
                    return {
                        'fonte': 'WIPO',
                        'publicacao': wo,
                        'titulo': None,
                        'titular': None,
                        'datas': {'deposito': None, 'publicacao': None, 'prioridade': None},
                        'worldwide_applications': {},
                        'paises_familia': [],
                        'erro': str(e),
                        'debug': {
                            'final_error': str(e),
                            'url': url
                        }
                    }
