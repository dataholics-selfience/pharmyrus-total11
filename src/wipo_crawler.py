"""WIPO Crawler v3.1 HOTFIX - Compact Version"""
import asyncio
import random
import logging
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WIPOCrawler:
    def __init__(self, max_retries: int = 5, timeout: int = 60000, headless: bool = True):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        logger.info("✅ WIPO Crawler initialized")
    
    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _normalize_wo(self, wo: str) -> str:
        wo = wo.upper().replace(' ', '').replace('-', '').replace('/', '')
        return wo if wo.startswith('WO') else 'WO' + wo
    
    async def _extract_basic(self, page: Page) -> Tuple[Dict, List[str]]:
        data = {
            'titulo': None, 'resumo': None, 'titular': None,
            'datas': {'deposito': None, 'publicacao': None, 'prioridade': None},
            'inventores': [], 'cpc_ipc': [], 'pdf_link': None
        }
        selectors = []
        
        # Título
        for sel in ['h3.tab_title', 'div.title', 'h1.patent-title']:
            try:
                elem = await page.query_selector(sel)
                if elem and (text := (await elem.inner_text()).strip()):
                    data['titulo'] = text
                    selectors.append(f"title:{sel}")
                    break
            except: pass
        
        # Resumo
        for sel in ['div.abstract', 'div#abstract', 'p.abstract-text']:
            try:
                elem = await page.query_selector(sel)
                if elem and (text := (await elem.inner_text()).strip()):
                    data['resumo'] = text[:500]
                    selectors.append(f"abstract:{sel}")
                    break
            except: pass
        
        # Titular
        for sel in ['td:has-text("Applicant") + td', 'td:has-text("Applicants") + td', '.applicantData']:
            try:
                elem = await page.query_selector(sel)
                if elem and (text := (await elem.inner_text()).strip()):
                    data['titular'] = text
                    selectors.append(f"applicant:{sel}")
                    break
            except: pass
        
        # Datas
        date_labels = {
            'deposito': ['Filing Date', 'Application Date'],
            'publicacao': ['Publication Date', 'International Publication Date'],
            'prioridade': ['Priority Date']
        }
        
        for date_type, labels in date_labels.items():
            for label in labels:
                try:
                    rows = await page.query_selector_all('tr')
                    for row in rows:
                        if label in await row.inner_text():
                            cells = await row.query_selector_all('td')
                            if len(cells) >= 2 and (date_val := (await cells[1].inner_text()).strip()):
                                data['datas'][date_type] = date_val[:10]
                                selectors.append(f"date_{date_type}")
                                break
                    if data['datas'][date_type]:
                        break
                except: pass
        
        return data, selectors
    
    async def _extract_worldwide(self, page: Page) -> Tuple[Dict, int]:
        worldwide = {}
        total = 0
        
        # Click National Phase tab
        for sel in ['a:has-text("National Phase")', 'button:has-text("National Phase")', '#national-phase-tab']:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    await elem.click()
                    await page.wait_for_timeout(3000)
                    logger.info(f"  ✅ Clicked National Phase: {sel}")
                    break
            except: pass
        
        # Extract table
        try:
            for table_sel in ['table.national-phase-table tr', 'div.national-phase tr', 'table tr']:
                rows = await page.query_selector_all(table_sel)
                if len(rows) > 1:
                    for row in rows[1:]:
                        try:
                            cells = await row.query_selector_all('td')
                            if len(cells) < 3:
                                continue
                            
                            filing_date = (await cells[0].inner_text()).strip()
                            country = (await cells[1].inner_text()).strip()
                            app_num = (await cells[2].inner_text()).strip() if len(cells) > 2 else ''
                            status = (await cells[3].inner_text()).strip() if len(cells) > 3 else ''
                            
                            if not country or len(country) > 3:
                                continue
                            
                            year = filing_date[:4] if len(filing_date) >= 4 else 'unknown'
                            
                            if year not in worldwide:
                                worldwide[year] = []
                            
                            worldwide[year].append({
                                'filing_date': filing_date,
                                'country_code': country,
                                'application_number': app_num,
                                'legal_status': status
                            })
                            total += 1
                        except: pass
                    break
        except Exception as e:
            logger.error(f"  Error extracting worldwide: {e}")
        
        logger.info(f"  📊 Worldwide: {total} apps from {len(worldwide)} years")
        return worldwide, total
    
    async def fetch_patent(self, wo_number: str) -> Dict[str, Any]:
        wo = self._normalize_wo(wo_number)
        url = f"https://patentscope.wipo.int/search/en/detail.jsf?docId={wo}"
        
        for retry in range(self.max_retries):
            try:
                logger.info(f"🔍 Fetching {wo} (attempt {retry + 1})")
                
                page = await self.context.new_page()
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                basic, selectors = await self._extract_basic(page)
                worldwide, total_apps = await self._extract_worldwide(page)
                
                countries = sorted(list(set(
                    app['country_code']
                    for apps in worldwide.values()
                    for app in apps
                    if app.get('country_code')
                )))
                
                await page.close()
                
                if not any([basic['titulo'], basic['resumo'], basic['titular'], worldwide]):
                    raise ValueError("No data extracted")
                
                result = {
                    'fonte': 'WIPO',
                    'publicacao': wo,
                    'titulo': basic['titulo'],
                    'resumo': basic['resumo'],
                    'titular': basic['titular'],
                    'datas': basic['datas'],
                    'inventores': basic['inventores'],
                    'cpc_ipc': basic['cpc_ipc'],
                    'pdf_link': basic['pdf_link'],
                    'worldwide_applications': worldwide,
                    'paises_familia': countries,
                    'debug': {
                        'selectors_found': selectors,
                        'total_worldwide_apps': total_apps,
                        'countries_found': len(countries),
                        'retry_attempt': retry + 1
                    }
                }
                
                logger.info(f"✅ {wo}: {total_apps} apps, {len(countries)} countries")
                return result
            
            except Exception as e:
                logger.error(f"❌ Attempt {retry + 1} failed: {e}")
                
                if retry < self.max_retries - 1:
                    wait = (2 ** retry) + random.uniform(0, 1)
                    await asyncio.sleep(wait)
                else:
                    return {
                        'fonte': 'WIPO',
                        'publicacao': wo,
                        'titulo': None,
                        'titular': None,
                        'datas': {'deposito': None, 'publicacao': None, 'prioridade': None},
                        'worldwide_applications': {},
                        'paises_familia': [],
                        'erro': str(e),
                        'debug': {'final_error': str(e)}
                    }
