"""
Pipeline Service v3.1 HOTFIX - Complete Patent Intelligence Pipeline
CRITICAL FIXES:
- WO discovery with 20+ parallel queries
- Local WIPO crawler integration (no external API)
- Layered debug system
- Complete worldwide applications processing
"""
import asyncio
import aiohttp
import logging
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .wipo_crawler import WIPOCrawler

logger = logging.getLogger(__name__)

class PipelineService:
    """
    Complete patent intelligence pipeline
    
    LAYERS:
    1. PubChem - Molecular data (CAS, dev codes, synonyms)
    2. WO Discovery - Find WO patents (20+ parallel queries)
    3. WIPO Details - Extract complete patent data
    4. INPI Brasil - Direct BR patent search
    5. FDA - Approval status
    6. ClinicalTrials - Trial data
    """
    
    def __init__(self):
        self.pubchem_base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        self.serpapi_key = "3f22448f4d43ce8259fa2f7f6385222323a67c4ce4e72fcc774b43d23812889d"
        self.inpi_api = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
    
    async def execute_full_pipeline(
        self,
        molecule: str,
        country_filter: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Execute complete pipeline with all layers
        """
        start_time = time.time()
        debug_info = {
            'layers': [],
            'timings': {},
            'errors_count': 0,
            'warnings_count': 0
        }
        
        logger.info(f"🚀 Pipeline START: {molecule}")
        
        # LAYER 1: PubChem
        layer1_start = time.time()
        pubchem_data = await self._layer1_pubchem(molecule)
        debug_info['timings']['pubchem'] = round(time.time() - layer1_start, 2)
        debug_info['layers'].append({
            'layer': 'Layer 1: PubChem',
            'status': 'success' if pubchem_data else 'failed',
            'duration_seconds': debug_info['timings']['pubchem'],
            'data_points': len(pubchem_data.get('dev_codes', [])) if pubchem_data else 0
        })
        
        # LAYER 2: WO Discovery (FIXED!)
        layer2_start = time.time()
        wo_numbers = await self._layer2_discover_wos(molecule, pubchem_data)
        debug_info['timings']['wo_discovery'] = round(time.time() - layer2_start, 2)
        debug_info['layers'].append({
            'layer': 'Layer 2: WO Discovery',
            'status': 'success',
            'duration_seconds': debug_info['timings']['wo_discovery'],
            'data_points': len(wo_numbers),
            'details': f"Found {len(wo_numbers)} WO patents from parallel queries"
        })
        
        # Apply limit
        wo_numbers = wo_numbers[:limit]
        
        # LAYER 3: WIPO Patent Details (FIXED!)
        layer3_start = time.time()
        wo_patents = await self._layer3_patent_details(wo_numbers, country_filter)
        debug_info['timings']['parallel_batch'] = round(time.time() - layer3_start, 2)
        debug_info['layers'].append({
            'layer': 'Layer 3: WIPO Details',
            'status': 'success',
            'duration_seconds': debug_info['timings']['parallel_batch'],
            'data_points': len(wo_patents),
            'details': f"Processed {len(wo_numbers)} WO patents with complete data"
        })
        
        # LAYER 4: INPI Brasil
        layer4_start = time.time()
        br_patents_inpi = await self._layer4_inpi_brasil(molecule, pubchem_data)
        debug_info['timings']['inpi'] = round(time.time() - layer4_start, 2)
        debug_info['layers'].append({
            'layer': 'Layer 4: INPI Brasil',
            'status': 'success',
            'duration_seconds': debug_info['timings']['inpi'],
            'data_points': len(br_patents_inpi)
        })
        
        # LAYER 5: FDA (optional)
        fda_status = await self._layer5_fda(molecule)
        
        # LAYER 6: ClinicalTrials (optional)
        clinical_trials = await self._layer6_clinical_trials(molecule)
        
        # Build final result
        total_duration = time.time() - start_time
        debug_info['timings']['total'] = round(total_duration, 2)
        
        all_patents = wo_patents + br_patents_inpi
        
        # Count by jurisdiction
        jurisdictions = {}
        for p in all_patents:
            pub_num = p.get('publication_number', '')
            if 'BR' in pub_num:
                jurisdictions['brazil'] = jurisdictions.get('brazil', 0) + 1
            elif 'US' in pub_num:
                jurisdictions['usa'] = jurisdictions.get('usa', 0) + 1
            elif 'EP' in pub_num:
                jurisdictions['europe'] = jurisdictions.get('europe', 0) + 1
            elif 'WO' in pub_num:
                jurisdictions['wipo'] = jurisdictions.get('wipo', 0) + 1
        
        result = {
            'executive_summary': {
                'molecule_name': molecule,
                'total_patents': len(all_patents),
                'wo_patents_found': len(wo_patents),
                'br_patents_inpi': len(br_patents_inpi),
                'jurisdictions': jurisdictions,
                'fda_status': fda_status.get('status') if fda_status else 'unknown',
                'clinical_trials_count': clinical_trials.get('total', 0) if clinical_trials else 0,
                'pubchem_data': pubchem_data,
                'country_filter_applied': country_filter
            },
            'wo_patents': wo_patents,
            'br_patents_inpi': br_patents_inpi,
            'all_patents': all_patents,
            'fda_data': fda_status,
            'clinical_trials': clinical_trials,
            'debug_info': debug_info,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Pipeline COMPLETE: {len(all_patents)} patents in {total_duration:.1f}s")
        return result
    
    async def _layer1_pubchem(self, molecule: str) -> Optional[Dict[str, Any]]:
        """Layer 1: PubChem molecular data"""
        try:
            url = f"{self.pubchem_base}/compound/name/{molecule}/synonyms/JSON"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    syns = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                    
                    dev_codes = []
                    cas = None
                    
                    for s in syns:
                        # Dev codes pattern: XX-12345
                        if re.match(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', s, re.IGNORECASE):
                            if len(dev_codes) < 10:
                                dev_codes.append(s)
                        
                        # CAS number pattern: 12345-67-8
                        if re.match(r'^\d{2,7}-\d{2}-\d$', s) and not cas:
                            cas = s
                    
                    logger.info(f"  📦 PubChem: {len(dev_codes)} dev codes, CAS={cas}")
                    
                    return {
                        'dev_codes': dev_codes,
                        'cas': cas,
                        'synonyms': syns[:50]  # First 50 synonyms
                    }
        
        except Exception as e:
            logger.error(f"  ❌ PubChem error: {e}")
            return None
    
    async def _layer2_discover_wos(
        self,
        molecule: str,
        pubchem_data: Optional[Dict] = None
    ) -> List[str]:
        """
        Layer 2: WO Discovery with multiple parallel queries
        
        CRITICAL FIX v3.1: Now executes 20+ queries in parallel
        """
        dev_codes = pubchem_data.get('dev_codes', []) if pubchem_data else []
        
        # Build search queries
        queries = []
        
        # Year-based queries (2011-2024)
        for year in range(2011, 2025):
            queries.append(f"{molecule} patent WO{year}")
        
        # Dev code queries (top 5)
        for dev in dev_codes[:5]:
            queries.append(f"{dev} patent WO")
        
        # Company-specific queries
        queries.append(f"{molecule} Orion Corporation patent")
        queries.append(f"{molecule} Bayer patent")
        
        # Quoted variations
        queries.append(f'"{molecule}" patent WO')
        
        logger.info(f"  🔍 WO Discovery: {len(queries)} parallel queries")
        
        # Execute all queries in parallel
        tasks = [self._google_search_wo(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract WO numbers from all results
        wo_numbers = set()
        wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', re.IGNORECASE)
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            for item in result.get('organic_results', []):
                text = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('link', '')}"
                
                for match in wo_pattern.finditer(text):
                    wo = f"WO{match.group(1)}{match.group(2)}"
                    wo_numbers.add(wo)
        
        wo_list = sorted(list(wo_numbers))
        logger.info(f"  ✅ WO Discovery: {len(wo_list)} unique WO patents found")
        
        return wo_list
    
    async def _google_search_wo(self, query: str) -> Dict:
        """Execute single Google search via SerpAPI"""
        try:
            url = "https://serpapi.com/search.json"
            params = {
                'engine': 'google',
                'q': query,
                'api_key': self.serpapi_key,
                'num': 10
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {}
        
        except Exception as e:
            logger.warning(f"  ⚠️ Search failed for: {query}")
            return {}
    
    async def _layer3_patent_details(
        self,
        wo_numbers: List[str],
        country_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Layer 3: WIPO Patent Details with LOCAL crawler
        
        CRITICAL FIX v3.1: Uses local WIPOCrawler instead of external API
        """
        if not wo_numbers:
            return []
        
        logger.info(f"  🔄 Processing {len(wo_numbers)} WO patents...")
        
        patents = []
        errors = 0
        
        # Use local crawler with context manager
        async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
            for i, wo in enumerate(wo_numbers):
                try:
                    logger.info(f"  [{i+1}/{len(wo_numbers)}] Processing {wo}")
                    
                    data = await crawler.fetch_patent(wo)
                    
                    if data.get('erro'):
                        errors += 1
                        continue
                    
                    # Filter by country if requested
                    if country_filter:
                        worldwide = data.get('worldwide_applications', {})
                        filtered_apps = {}
                        
                        for year, apps in worldwide.items():
                            filtered = [app for app in apps if app.get('country_code') == country_filter]
                            if filtered:
                                filtered_apps[year] = filtered
                        
                        data['worldwide_applications'] = filtered_apps
                    
                    # Count total applications
                    total_apps = sum(
                        len(apps)
                        for apps in data.get('worldwide_applications', {}).values()
                    )
                    
                    logger.info(f"  ✅ {wo}: {total_apps} aplicações worldwide")
                    
                    patents.append({
                        'publication_number': wo,
                        'title': data.get('titulo'),
                        'abstract': data.get('resumo'),
                        'applicant': data.get('titular'),
                        'filing_date': data.get('datas', {}).get('deposito'),
                        'publication_date': data.get('datas', {}).get('publicacao'),
                        'inventors': data.get('inventores'),
                        'ipc_cpc': data.get('cpc_ipc'),
                        'pdf_link': data.get('pdf_link'),
                        'worldwide_applications': data.get('worldwide_applications'),
                        'countries': data.get('paises_familia'),
                        'debug': data.get('debug'),
                        'source': 'WIPO'
                    })
                
                except Exception as e:
                    logger.error(f"  ❌ Error processing {wo}: {e}")
                    errors += 1
        
        logger.info(f"  ✅ Layer 3 complete: {len(patents)} patents, {errors} errors")
        return patents
    
    async def _layer4_inpi_brasil(
        self,
        molecule: str,
        pubchem_data: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Layer 4: INPI Brasil direct search"""
        try:
            params = {'medicine': molecule}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.inpi_api, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        return []
                    
                    data = await resp.json()
                    patents_data = data.get('data', [])
                    
                    patents = []
                    for p in patents_data:
                        if p.get('title', '').startswith('BR'):
                            patents.append({
                                'publication_number': p.get('title', '').replace(' ', '-'),
                                'title': p.get('applicant', ''),
                                'abstract': p.get('fullText', '')[:300],
                                'filing_date': p.get('depositDate', ''),
                                'link': f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={p.get('title', '')}",
                                'source': 'INPI'
                            })
                    
                    logger.info(f"  📄 INPI Brasil: {len(patents)} patents")
                    return patents
        
        except Exception as e:
            logger.error(f"  ❌ INPI error: {e}")
            return []
    
    async def _layer5_fda(self, molecule: str) -> Optional[Dict[str, Any]]:
        """Layer 5: FDA approval status"""
        try:
            url = f"https://api.fda.gov/drug/ndc.json"
            params = {'search': f'generic_name:{molecule}', 'limit': 1}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get('results', [])
                        
                        if results:
                            return {
                                'status': 'Approved',
                                'labeler': results[0].get('labeler_name'),
                                'product_ndc': results[0].get('product_ndc')
                            }
        
        except:
            pass
        
        return {'status': 'Not Found'}
    
    async def _layer6_clinical_trials(self, molecule: str) -> Optional[Dict[str, Any]]:
        """Layer 6: ClinicalTrials.gov data"""
        try:
            url = f"https://clinicaltrials.gov/api/v2/studies"
            params = {'query.term': molecule, 'pageSize': 10}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        total = data.get('totalCount', 0)
                        
                        return {
                            'total': total,
                            'status': 'Active' if total > 0 else 'None Found'
                        }
        
        except:
            pass
        
        return {'total': 0, 'status': 'Unknown'}
