"""
WIPO Crawler v3.1 HOTFIX - Complete Patent Data Extraction
CRITICAL FIXES:
- Extracts worldwide_applications from National Phase tab
- Multiple selector strategies for titular, dates, inventors
- Exponential backoff retry system
- Debug tracking of successful extractions
"""
import asyncio
import random
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WIPOCrawler:
    """
    WIPO Patentscope crawler with complete data extraction
    
    v3.1 HOTFIX Features:
    - Extracts worldwide_applications (70+ countries)
    - Multiple selectors for each field (titular, dates, inventors)
    - Retry with exponential backoff
    - Debug metadata for troubleshooting
    """
    
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
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        logger.info("✅ WIPO Crawler initialized")
    
    async def close(self):
        """Close browser and playwright"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("🛑 WIPO Crawler closed")
    
    def _normalize_wo_number(self, wo_number: str) -> str:
        """Normalize WO number format"""
        wo = wo_number.upper().replace(' ', '').replace('-', '').replace('/', '')
        if not wo.startswith('WO'):
            wo = 'WO' + wo
        return wo
    
    async def _extract_basic_data(self, page: Page) -> Tuple[Dict[str, Any], List[str]]:
        """
        Extract basic patent data with multiple selector strategies
        Returns: (data_dict, selectors_found_list)
        """
        data = {
            'titulo': None,
            'resumo': None,
            'titular': None,
            'datas': {'deposito': None, 'publicacao': None, 'prioridade': None},
            'inventores': [],
            'cpc_ipc': [],
            'pdf_link': None
        }
        selectors_found = []
        
        # TÍTULO - múltiplas estratégias
        titulo_selectors = [
            'h3.tab_title',
            'div.title',
            'h1.patent-title',
            'span.patentTitle'
        ]
        for sel in titulo_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    data['titulo'] = (await elem.inner_text()).strip()
                    if data['titulo']:
                        selectors_found.append(f"title:{sel}")
                        break
            except:
                continue
        
        # RESUMO
        resumo_selectors = [
            'div.abstract',
            'div#abstract',
            'p.abstract-text',
            'div.description'
        ]
        for sel in resumo_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    data['resumo'] = (await elem.inner_text()).strip()[:500]
                    if data['resumo']:
                        selectors_found.append(f"abstract:{sel}")
                        break
            except:
                continue
        
        # TITULAR/APPLICANT - múltiplas estratégias
        titular_selectors = [
            'td:has-text("Applicant") + td',
            'td:has-text("Applicants") + td',
            '.applicantData',
            'div.applicant',
            'span.applicant-name'
        ]
        for sel in titular_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    data['titular'] = (await elem.inner_text()).strip()
                    if data['titular']:
                        selectors_found.append(f"applicant:{sel}")
                        break
            except:
                continue
        
        # DATAS - extrair de tabela
        date_labels = {
            'deposito': ['Filing Date', 'Application Date', 'International Filing Date'],
            'publicacao': ['Publication Date', 'International Publication Date'],
            'prioridade': ['Priority Date', 'Priority']
        }
        
        for date_type, labels in date_labels.items():
            for label in labels:
                try:
                    rows = await page.query_selector_all('tr')
                    for row in rows:
                        text = await row.inner_text()
                        if label in text:
                            cells = await row.query_selector_all('td')
                            if len(cells) >= 2:
                                date_val = (await cells[1].inner_text()).strip()
                                if date_val and len(date_val) >= 8:
                                    data['datas'][date_type] = date_val[:10]
                                    selectors_found.append(f"date_{date_type}:{label}")
                                    break
                    if data['datas'][date_type]:
                        break
                except:
                    continue
        
        # INVENTORES
        inventor_selectors = [
            'td:has-text("Inventor") + td',
            'td:has-text("Inventors") + td',
            '.inventorData',
            'div.inventor'
        ]
        for sel in inventor_selectors:
            try:
                elems = await page.query_selector_all(sel)
                inventors_found = []
                for elem in elems:
                    inv_text = (await elem.inner_text()).strip()
                    # Split por ; ou ,
                    for inv in inv_text.replace(';', ',').split(','):
                        inv = inv.strip()
                        if inv and len(inv) > 2 and inv not in inventors_found:
                            inventors_found.append(inv)
                
                if inventors_found:
                    data['inventores'] = inventors_found
                    selectors_found.append(f"inventors:{sel}")
                    break
            except:
                continue
        
        # CPC/IPC
        try:
            cpc_elems = await page.query_selector_all('.cpc, .ipc, td:has-text("IPC") + td')
            for elem in cpc_elems:
                text = (await elem.inner_text()).strip()
                if text and len(text) < 50:
                    data['cpc_ipc'].append(text)
            if data['cpc_ipc']:
                selectors_found.append("cpc_ipc:found")
        except:
            pass
        
        # PDF LINK
        try:
            pdf_elem = await page.query_selector('a[href*="pdf"], a:has-text("PDF")')
            if pdf_elem:
                data['pdf_link'] = await pdf_elem.get_attribute('href')
                if data['pdf_link'] and not data['pdf_link'].startswith('http'):
                    data['pdf_link'] = 'https://patentscope.wipo.int' + data['pdf_link']
                selectors_found.append("pdf:found")
        except:
            pass
        
        return data, selectors_found
    
    async def _extract_worldwide_applications(self, page: Page) -> Tuple[Dict[str, List[Dict]], int]:
        """
        Extract worldwide applications from National Phase tab
        Returns: (worldwide_dict, total_count)
        
        CRITICAL FIX: This was missing in v3.0!
        """
        worldwide = {}
        total_count = 0
        
        # Estratégia 1: Clicar na aba "National Phase"
        national_phase_clicked = False
        click_selectors = [
            'a:has-text("National Phase")',
            'button:has-text("National Phase")',
            'li:has-text("National Phase")',
            '#national-phase-tab',
            'a[href*="national"]'
        ]
        
        for sel in click_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    await elem.click()
                    await page.wait_for_timeout(3000)  # Esperar carregar
                    national_phase_clicked = True
                    logger.info(f"  ✅ Clicked National Phase tab: {sel}")
                    break
            except:
                continue
        
        if not national_phase_clicked:
            logger.warning("  ⚠️ Could not click National Phase tab")
            return worldwide, 0
        
        # Estratégia 2: Extrair tabela de aplicações
        try:
            # Selecionar todas as linhas da tabela
            table_selectors = [
                'table.national-phase-table tr',
                'div.national-phase tr',
                'table tr',
                '.application-row'
            ]
            
            rows_found = []
            for table_sel in table_selectors:
                try:
                    rows = await page.query_selector_all(table_sel)
                    if len(rows) > 1:  # Mais de 1 = header + dados
                        rows_found = rows
                        break
                except:
                    continue
            
            if not rows_found:
                logger.warning("  ⚠️ No table rows found")
                return worldwide, 0
            
            # Parse cada linha
            for row in rows_found[1:]:  # Skip header
                try:
                    cells = await row.query_selector_all('td')
                    if len(cells) < 3:
                        continue
                    
                    # Extrair dados das células
                    filing_date = (await cells[0].inner_text()).strip()
                    country_code = (await cells[1].inner_text()).strip()
                    app_number = (await cells[2].inner_text()).strip() if len(cells) > 2 else ''
                    legal_status = (await cells[3].inner_text()).strip() if len(cells) > 3 else ''
                    
                    if not country_code or len(country_code) > 3:
                        continue
                    
                    # Agrupar por ano
                    year = filing_date[:4] if len(filing_date) >= 4 else 'unknown'
                    
                    app_data = {
                        'filing_date': filing_date,
                        'country_code': country_code,
                        'application_number': app_number,
                        'legal_status': legal_status,
                        'legal_status_cat': 'active' if 'grant' in legal_status.lower() else 'pending'
                    }
                    
                    if year not in worldwide:
                        worldwide[year] = []
                    
                    worldwide[year].append(app_data)
                    total_count += 1
                
                except Exception as e:
                    continue
        
        except Exception as e:
            logger.error(f"  ❌ Error parsing worldwide table: {e}")
        
        # Estratégia 3: Fallback - extrair códigos de países de outros elementos
        if total_count == 0:
            try:
                country_elems = await page.query_selector_all('.country-code, span[data-country]')
                for elem in country_elems:
                    country = (await elem.inner_text()).strip()
                    if len(country) == 2:
                        if 'unknown' not in worldwide:
                            worldwide['unknown'] = []
                        worldwide['unknown'].append({
                            'country_code': country,
                            'filing_date': '',
                            'application_number': '',
                            'legal_status': '',
                            'legal_status_cat': 'unknown'
                        })
                        total_count += 1
            except:
                pass
        
        logger.info(f"  📊 Worldwide applications: {total_count} from {len(worldwide)} years")
        return worldwide, total_count
    
    async def _extract_br_patents(self, worldwide_applications: Dict) -> List[Dict]:
        """Extract only BR patents from worldwide applications"""
        br_patents = []
        
        for year, apps in worldwide_applications.items():
            for app in apps:
                if app.get('country_code') == 'BR':
                    br_patents.append({
                        'number': app.get('application_number', ''),
                        'filing_date': app.get('filing_date', ''),
                        'legal_status': app.get('legal_status', ''),
                        'year': year
                    })
        
        return br_patents
    
    async def fetch_patent(self, wo_number: str) -> Dict[str, Any]:
        """
        Fetch complete patent data with all fixes from v3.1 HOTFIX
        
        EXTRACTION STEPS:
        1. Load page
        2. Extract basic data (title, abstract, applicant, dates)
        3. Click National Phase tab
        4. Extract worldwide applications table
        5. Filter BR patents
        6. Build countries list
        7. Return structured data with debug info
        """
        wo = self._normalize_wo_number(wo_number)
        url = f"https://patentscope.wipo.int/search/en/detail.jsf?docId={wo}"
        
        for retry in range(self.max_retries):
            try:
                logger.info(f"🔍 Fetching {wo} (attempt {retry + 1}/{self.max_retries})")
                
                page = await self.context.new_page()
                await page.goto(url, timeout=self.timeout, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
                # STEP 1: Extract basic data
                basic_data, selectors_found = await self._extract_basic_data(page)
                
                # STEP 2: Extract worldwide applications
                worldwide_apps, total_apps = await self._extract_worldwide_applications(page)
                
                # STEP 3: Extract BR patents
                br_patents = self._extract_br_patents(worldwide_apps)
                
                # STEP 4: Build countries list
                countries = list(set(
                    app.get('country_code', '')
                    for year_apps in worldwide_apps.values()
                    for app in year_apps
                    if app.get('country_code')
                ))
                countries.sort()
                
                await page.close()
                
                # Validação: requer pelo menos algum dado válido
                has_data = any([
                    basic_data['titulo'],
                    basic_data['resumo'],
                    basic_data['titular'],
                    len(worldwide_apps) > 0
                ])
                
                if not has_data:
                    raise ValueError("No data extracted - all fields are null/empty")
                
                # Build final result
                result = {
                    'fonte': 'WIPO',
                    'publicacao': wo,
                    'titulo': basic_data['titulo'],
                    'resumo': basic_data['resumo'],
                    'titular': basic_data['titular'],
                    'datas': basic_data['datas'],
                    'inventores': basic_data['inventores'],
                    'cpc_ipc': basic_data['cpc_ipc'],
                    'pdf_link': basic_data['pdf_link'],
                    'worldwide_applications': worldwide_apps,
                    'paises_familia': countries,
                    'debug': {
                        'extraction_method': 'playwright',
                        'selectors_found': selectors_found,
                        'total_worldwide_apps': total_apps,
                        'br_patents_found': len(br_patents),
                        'countries_found': len(countries),
                        'retry_attempt': retry + 1
                    }
                }
                
                logger.info(f"✅ {wo}: {total_apps} worldwide apps, {len(br_patents)} BR patents")
                return result
            
            except Exception as e:
                logger.error(f"❌ Attempt {retry + 1} failed: {e}")
                
                if retry < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** retry) + random.uniform(0, 1)
                    logger.info(f"⏳ Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    # Final failure
                    return {
                        'fonte': 'WIPO',
                        'publicacao': wo,
                        'titulo': None,
                        'resumo': None,
                        'titular': None,
                        'datas': {'deposito': None, 'publicacao': None, 'prioridade': None},
                        'inventores': [],
                        'cpc_ipc': [],
                        'pdf_link': None,
                        'worldwide_applications': {},
                        'paises_familia': [],
                        'erro': str(e),
                        'debug': {
                            'extraction_method': 'playwright',
                            'selectors_found': [],
                            'total_worldwide_apps': 0,
                            'br_patents_found': 0,
                            'countries_found': 0,
                            'retry_attempts': self.max_retries,
                            'final_error': str(e)
                        }
                    }
