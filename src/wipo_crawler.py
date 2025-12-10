#!/usr/bin/env python3
"""
WIPO Patentscope Advanced Crawler - v3.1 HOTFIX
Pharmyrus - Patent Intelligence Platform

CORREÇÕES:
- Extração completa de worldwide_applications (igual ao /test/)
- Extração de titular, datas, inventores do HTML
- Sistema de debug detalhado por camadas
- Retry inteligente com exponential backoff
"""

import asyncio
import random
import time
import json
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
import logging

logger = logging.getLogger(__name__)


class WIPOCrawler:
    """Crawler robusto para WIPO Patentscope com extração completa de dados"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, max_retries: int = 5, timeout: int = 60000, headless: bool = True):
        self.max_retries = max_retries
        self.timeout = timeout
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def initialize(self):
        """Inicializa o browser"""
        logger.info("🚀 Inicializando Playwright...")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--window-size=1920,1080'
            ]
        )
        
        logger.info("✅ Browser inicializado")
        
    async def close(self):
        """Fecha o browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def _create_stealth_page(self) -> Page:
        """Cria página com configurações stealth"""
        context = await self.browser.new_context(
            user_agent=random.choice(self.USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)
        
        return await context.new_page()
    
    async def _wait_for_load(self, page: Page, selectors: List[str], timeout: int = 30000):
        """Espera inteligente por elementos"""
        start = time.time()
        
        while time.time() - start < timeout / 1000:
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=2000, state='visible')
                    return True
                except PlaywrightTimeout:
                    continue
            await asyncio.sleep(1)
        
        return False
    
    async def _extract_basic_data(self, page: Page, wo_number: str) -> Dict[str, Any]:
        """Extrai dados básicos da página"""
        data = {
            'fonte': 'WIPO',
            'pais': 'WO',
            'publicacao': wo_number,
            'pedido': None,
            'titulo': None,
            'titular': None,
            'datas': {
                'deposito': None,
                'publicacao': None,
                'prioridade': None
            },
            'inventores': [],
            'cpc_ipc': [],
            'resumo': None,
            'paises_familia': [],
            'documentos': {
                'pdf_link': None,
                'patentscope_link': f"https://patentscope.wipo.int/search/en/detail.jsf?docId={wo_number}"
            },
            'worldwide_applications': {},
            'debug': {
                'extraction_method': 'playwright',
                'selectors_found': []
            }
        }
        
        try:
            # Título (múltiplos seletores)
            for selector in ['h3.tab_title', '.patent-title', 'h1', '.resultTitle']:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = (await elem.inner_text()).strip()
                        if text and len(text) > 10:
                            # Remove número WO do título se presente
                            data['titulo'] = text.replace(wo_number, '').strip()
                            data['debug']['selectors_found'].append(f'title:{selector}')
                            break
                except:
                    continue
                    
            # Resumo
            for selector in ['div.abstract', '.patent-abstract', '#abstract', '.abstractDataTitle']:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = (await elem.inner_text()).strip()
                        if text and len(text) > 20:
                            data['resumo'] = text
                            data['debug']['selectors_found'].append(f'abstract:{selector}')
                            break
                except:
                    continue
                    
            # Titular/Applicant
            for selector in [
                'td:has-text("Applicant") + td',
                'td:has-text("Applicants") + td',
                '.applicantData',
                'div.applicant'
            ]:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = (await elem.inner_text()).strip()
                        if text:
                            # Limpa formatação
                            lines = [l.strip() for l in text.split('\n') if l.strip()]
                            data['titular'] = lines[0] if lines else text
                            data['debug']['selectors_found'].append(f'applicant:{selector}')
                            break
                except:
                    continue
                    
            # Inventores
            for selector in [
                'td:has-text("Inventor") + td',
                'td:has-text("Inventors") + td',
                '.inventorData'
            ]:
                try:
                    elems = await page.query_selector_all(selector)
                    for elem in elems:
                        text = (await elem.inner_text()).strip()
                        if text:
                            inventors = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 5]
                            data['inventores'].extend(inventors)
                            data['debug']['selectors_found'].append(f'inventors:{selector}')
                except:
                    continue
            data['inventores'] = list(set(data['inventores']))[:10]  # Limit to 10 unique
                    
            # Datas
            date_mappings = [
                ('deposito', ['Filing Date', 'Application Date', 'International Filing Date']),
                ('publicacao', ['Publication Date', 'International Publication Date']),
                ('prioridade', ['Priority Date', 'Priority'])
            ]
            
            for field, labels in date_mappings:
                for label in labels:
                    try:
                        elem = await page.query_selector(f'td:has-text("{label}") + td')
                        if elem:
                            text = (await elem.inner_text()).strip()
                            if text and len(text) <= 20:  # Prevent picking up wrong data
                                data['datas'][field] = text
                                data['debug']['selectors_found'].append(f'date_{field}:{label}')
                                break
                    except:
                        continue
                    
            # Application Number
            try:
                elem = await page.query_selector('td:has-text("Application Number") + td, td:has-text("Int. Application No.") + td')
                if elem:
                    data['pedido'] = (await elem.inner_text()).strip()
                    data['debug']['selectors_found'].append('application_number')
            except:
                pass
                    
            # CPC/IPC Classifications
            for selector in ['.ipc', '.cpc', 'td:has-text("IPC") + td', 'td:has-text("CPC") + td']:
                try:
                    elems = await page.query_selector_all(selector)
                    for elem in elems:
                        text = (await elem.inner_text()).strip()
                        if text:
                            codes = [c.strip() for c in text.replace(';', ',').split(',') if c.strip()]
                            data['cpc_ipc'].extend(codes)
                            data['debug']['selectors_found'].append(f'classification:{selector}')
                except:
                    continue
            data['cpc_ipc'] = list(set(data['cpc_ipc']))[:100]  # Limit to 100 unique
                    
            # Link PDF
            try:
                pdf_link = await page.query_selector('a[href*=".pdf"], a:has-text("PDF"), a:has-text("Full Document")')
                if pdf_link:
                    href = await pdf_link.get_attribute('href')
                    if href:
                        data['documentos']['pdf_link'] = href if href.startswith('http') else f"https://patentscope.wipo.int{href}"
                        data['debug']['selectors_found'].append('pdf_link')
            except:
                pass
                    
        except Exception as e:
            logger.error(f"❌ Erro na extração básica: {e}")
            data['debug']['extraction_error'] = str(e)
            
        return data
    
    async def _extract_worldwide_applications(self, page: Page, wo_number: str) -> Dict[str, List[Dict]]:
        """
        Extrai worldwide applications (igual ao /test/ que funciona)
        CRÍTICO: Esta é a função que estava faltando!
        """
        worldwide = {}
        
        try:
            # Tenta clicar na aba "National Phase"
            logger.info(f"🌍 Buscando worldwide applications para {wo_number}...")
            
            # Múltiplas tentativas de localizar a aba
            tab_selectors = [
                'a:has-text("National Phase")',
                'button:has-text("National Phase")',
                'li:has-text("National Phase")',
                '#nationalPhaseTab',
                '.tab-national-phase'
            ]
            
            tab_clicked = False
            for selector in tab_selectors:
                try:
                    tab = await page.query_selector(selector)
                    if tab:
                        await tab.click()
                        await asyncio.sleep(3)  # Espera carregar
                        tab_clicked = True
                        logger.info(f"✅ Aba National Phase clicada via {selector}")
                        break
                except:
                    continue
            
            if not tab_clicked:
                logger.warning(f"⚠️ Não encontrou aba National Phase para {wo_number}")
                return worldwide
            
            # Espera tabela carregar
            await asyncio.sleep(2)
            
            # Extrai dados da tabela National Phase
            table_selectors = [
                'table.nationalPhase',
                'table#nationalPhaseTable',
                'table.resultTable',
                'div.nationalPhase table'
            ]
            
            table_found = False
            for table_selector in table_selectors:
                try:
                    rows = await page.query_selector_all(f'{table_selector} tr')
                    if rows and len(rows) > 1:  # Has data rows
                        table_found = True
                        logger.info(f"📊 Encontrou {len(rows)-1} linhas na tabela")
                        
                        for row in rows[1:]:  # Skip header
                            try:
                                cells = await row.query_selector_all('td')
                                if len(cells) >= 3:
                                    filing_date = (await cells[0].inner_text()).strip()
                                    country_code = (await cells[1].inner_text()).strip()
                                    app_number = (await cells[2].inner_text()).strip()
                                    
                                    # Extrai year do filing_date
                                    year = filing_date[:4] if len(filing_date) >= 4 else "Unknown"
                                    
                                    if country_code and len(country_code) == 2:
                                        if year not in worldwide:
                                            worldwide[year] = []
                                        
                                        # Tenta pegar mais dados se disponíveis
                                        legal_status = ""
                                        legal_status_cat = "unknown"
                                        doc_id = ""
                                        
                                        if len(cells) > 3:
                                            legal_status = (await cells[3].inner_text()).strip()
                                            if "grant" in legal_status.lower():
                                                legal_status_cat = "active"
                                            elif "withdraw" in legal_status.lower() or "abandon" in legal_status.lower():
                                                legal_status_cat = "not_active"
                                        
                                        worldwide[year].append({
                                            "filing_date": filing_date,
                                            "country_code": country_code,
                                            "application_number": app_number,
                                            "document_id": doc_id or f"patent/{country_code}{app_number}/en",
                                            "legal_status": legal_status,
                                            "legal_status_cat": legal_status_cat
                                        })
                            except Exception as e:
                                logger.debug(f"Erro processando linha: {e}")
                                continue
                        
                        break
                except Exception as e:
                    logger.debug(f"Erro com table selector {table_selector}: {e}")
                    continue
            
            if table_found:
                logger.info(f"✅ Extraído {sum(len(v) for v in worldwide.values())} aplicações worldwide")
            else:
                logger.warning(f"⚠️ Tabela National Phase não encontrada")
            
            # Também tenta extrair países da família diretamente
            country_elems = await page.query_selector_all('.country-code, td.country')
            for elem in country_elems:
                try:
                    country = (await elem.inner_text()).strip()
                    if country and len(country) == 2:
                        # Adiciona à estrutura se ainda não existe
                        year = "Unknown"
                        if year not in worldwide:
                            worldwide[year] = []
                        
                        # Verifica se já existe
                        exists = any(app['country_code'] == country for app in worldwide[year])
                        if not exists:
                            worldwide[year].append({
                                "filing_date": "",
                                "country_code": country,
                                "application_number": "",
                                "document_id": "",
                                "legal_status": "",
                                "legal_status_cat": "unknown"
                            })
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Erro extraindo worldwide applications: {e}")
        
        return worldwide
    
    async def _extract_br_patents(self, worldwide: Dict) -> List[Dict]:
        """Extrai apenas patentes BR do worldwide_applications"""
        br_patents = []
        
        for year, apps in worldwide.items():
            for app in apps:
                if app.get('country_code') == 'BR':
                    br_patents.append({
                        "number": app.get('application_number', '').replace(' ', ''),
                        "application_number": app.get('application_number', ''),
                        "filing_date": app.get('filing_date', ''),
                        "legal_status": app.get('legal_status', ''),
                        "legal_status_cat": app.get('legal_status_cat', 'unknown'),
                        "source": "worldwide_applications",
                        "year": year
                    })
        
        return br_patents
    
    async def fetch_patent(self, wo_number: str, retry_count: int = 0) -> Dict[str, Any]:
        """
        Busca dados COMPLETOS de uma patente WO
        
        CORREÇÃO v3.1 HOTFIX:
        - Extrai worldwide_applications (igual ao /test/)
        - Extrai titular, datas, inventores
        - Sistema de debug detalhado
        
        Args:
            wo_number: Número WO (ex: WO2018162793)
            retry_count: Contador de tentativas
            
        Returns:
            Dicionário com dados COMPLETOS da patente
        """
        start_time = time.time()
        wo_clean = wo_number.replace('WO', '').replace(' ', '').replace('/', '')
        url = f"https://patentscope.wipo.int/search/en/detail.jsf?docId=WO{wo_clean}"
        
        logger.info(f"🔍 [{retry_count + 1}/{self.max_retries}] Buscando {wo_number}")
        
        page = None
        
        try:
            page = await self._create_stealth_page()
            await asyncio.sleep(random.uniform(1, 3))
            
            response = await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            
            if not response or response.status != 200:
                raise Exception(f"Status HTTP: {response.status if response else 'No response'}")
                
            logger.info(f"✅ Página carregada (status {response.status})")
            
            # Espera elementos chave
            key_selectors = ['h3.tab_title', '.patent-title', 'div.abstract', 'h1', '.resultTitle']
            await self._wait_for_load(page, key_selectors, timeout=20000)
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Scroll para carregar lazy content
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
            await page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(1)
            
            # 1. Extrai dados básicos
            logger.info("📄 Extraindo dados básicos...")
            data = await self._extract_basic_data(page, wo_number)
            
            # 2. Extrai worldwide applications (CRÍTICO!)
            logger.info("🌍 Extraindo worldwide applications...")
            worldwide = await self._extract_worldwide_applications(page, wo_number)
            data['worldwide_applications'] = worldwide
            
            # 3. Extrai BR patents
            br_patents = await self._extract_br_patents(worldwide)
            if br_patents:
                logger.info(f"🇧🇷 Encontrou {len(br_patents)} patentes BR")
            
            # 4. Lista países da família
            all_countries = set()
            for year_apps in worldwide.values():
                for app in year_apps:
                    country = app.get('country_code')
                    if country:
                        all_countries.add(country)
            data['paises_familia'] = sorted(list(all_countries))
            
            # Metadados finais
            data['duracao_segundos'] = round(time.time() - start_time, 2)
            data['debug']['total_worldwide_apps'] = sum(len(v) for v in worldwide.values())
            data['debug']['br_patents_found'] = len(br_patents)
            data['debug']['countries_found'] = len(all_countries)
            
            # Validação de dados essenciais
            has_basic_data = bool(data['titulo'] or data['resumo'] or data['titular'])
            has_worldwide = len(worldwide) > 0
            
            if not has_basic_data and not has_worldwide:
                raise Exception("Nenhum dado essencial extraído (nem básico nem worldwide)")
                
            logger.info(f"✅ SUCESSO! Duração: {data['duracao_segundos']}s | Worldwide: {data['debug']['total_worldwide_apps']} apps | BR: {len(br_patents)}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            
            if retry_count < self.max_retries - 1:
                wait_time = (2 ** retry_count) + random.uniform(0, 1)
                logger.info(f"⏳ Retry em {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                
                if page:
                    try:
                        await page.close()
                    except:
                        pass
                        
                return await self.fetch_patent(wo_number, retry_count + 1)
            else:
                logger.error(f"❌ Falha após {self.max_retries} tentativas")
                return {
                    'fonte': 'WIPO',
                    'pais': 'WO',
                    'publicacao': wo_number,
                    'erro': str(e),
                    'status': 'FALHA',
                    'duracao_segundos': round(time.time() - start_time, 2),
                    'documentos': {'patentscope_link': url},
                    'worldwide_applications': {},
                    'debug': {
                        'error': str(e),
                        'retry_count': retry_count
                    }
                }
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
    
    async def fetch_multiple_patents(self, wo_numbers: List[str]) -> List[Dict[str, Any]]:
        """Busca múltiplas patentes sequencialmente"""
        results = []
        
        for i, wo in enumerate(wo_numbers, 1):
            logger.info(f"\n📍 Patente {i}/{len(wo_numbers)}: {wo}")
            
            result = await self.fetch_patent(wo)
            results.append(result)
            
            if i < len(wo_numbers):
                delay = random.uniform(3, 6)
                logger.info(f"⏸️  Delay de {delay:.1f}s antes da próxima...")
                await asyncio.sleep(delay)
                
        return results
