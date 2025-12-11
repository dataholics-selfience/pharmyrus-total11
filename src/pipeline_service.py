"""Pipeline Service v3.1 HOTFIX - Compact"""
import asyncio
import logging
import aiohttp
from typing import Dict, Any, List
from .crawler_pool import crawler_pool

logger = logging.getLogger(__name__)

async def _get_pubchem_data(molecule: str) -> Dict:
    """Get dev codes and CAS from PubChem"""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    syns = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                    
                    dev_codes = [s for s in syns if len(s) < 20 and any(c.isdigit() for c in s) and any(c.isalpha() for c in s)][:10]
                    cas = next((s for s in syns if len(s.split('-')) == 3 and all(p.isdigit() for p in s.split('-'))), None)
                    
                    logger.info(f"PubChem: {len(dev_codes)} dev codes, CAS={cas}")
                    return {'dev_codes': dev_codes, 'cas': cas}
    except Exception as e:
        logger.error(f"PubChem error: {e}")
    
    return {'dev_codes': [], 'cas': None}

async def _discover_wo_numbers(molecule: str, dev_codes: List[str]) -> List[str]:
    """Discover WO numbers from multiple sources"""
    wo_numbers = set()
    queries = []
    
    # Year-based queries
    for year in range(2011, 2025):
        queries.append(f"{molecule} patent WO{year}")
    
    # Dev code queries
    for code in dev_codes[:5]:
        queries.append(f"{code} patent WO")
    
    # Company queries
    queries.extend([
        f"{molecule} Orion Corporation patent",
        f"{molecule} Bayer patent",
        f"{molecule} Pfizer patent"
    ])
    
    logger.info(f"🔍 Running {len(queries)} parallel WO searches...")
    
    async def search_google(query: str):
        try:
            api_key = "3f22448f4d43ce8259fa2f7f6385222323a67c4ce4e72fcc774b43d23812889d"
            url = f"https://serpapi.com/search.json?engine=google&q={query}&api_key={api_key}&num=10"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = str(data.get('organic_results', []))
                        
                        import re
                        matches = re.findall(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', text, re.IGNORECASE)
                        for match in matches:
                            wo_numbers.add(f"WO{match[0]}{match[1]}")
        except Exception as e:
            logger.debug(f"Search error: {e}")
    
    await asyncio.gather(*[search_google(q) for q in queries], return_exceptions=True)
    
    result = sorted(list(wo_numbers))
    logger.info(f"✅ Found {len(result)} unique WO numbers")
    return result

async def _process_wo_batch(wo_numbers: List[str]) -> List[Dict]:
    """Process WO numbers in parallel"""
    results = []
    
    async def fetch_one(wo: str):
        try:
            crawler = crawler_pool.get_crawler()
            return await crawler.fetch_patent(wo)
        except Exception as e:
            logger.error(f"Error fetching {wo}: {e}")
            return {'publicacao': wo, 'erro': str(e)}
    
    results = await asyncio.gather(*[fetch_one(wo) for wo in wo_numbers], return_exceptions=True)
    
    valid = [r for r in results if isinstance(r, dict) and not r.get('erro')]
    logger.info(f"✅ Processed {len(valid)}/{len(wo_numbers)} WO numbers successfully")
    
    return valid

async def pipeline_search(molecule: str, max_wos: int = 5) -> Dict[str, Any]:
    """Full pipeline: PubChem → WO Discovery → WIPO Details → BR Extraction"""
    logger.info(f"🚀 Starting pipeline for: {molecule}")
    
    # Step 1: PubChem
    pubchem = await _get_pubchem_data(molecule)
    
    # Step 2: WO Discovery
    wo_numbers = await _discover_wo_numbers(molecule, pubchem['dev_codes'])
    
    # Step 3: Process WOs (limited)
    wo_to_process = wo_numbers[:max_wos]
    wo_results = await _process_wo_batch(wo_to_process)
    
    # Step 4: Extract BR patents
    br_patents = []
    for wo in wo_results:
        for year, apps in wo.get('worldwide_applications', {}).items():
            for app in apps:
                if app.get('country_code') == 'BR':
                    br_patents.append({
                        'wo_number': wo['publicacao'],
                        'filing_date': app['filing_date'],
                        'application_number': app['application_number'],
                        'legal_status': app.get('legal_status', ''),
                        'source': 'WIPO'
                    })
    
    logger.info(f"✅ Pipeline complete: {len(br_patents)} BR patents from {len(wo_results)} WOs")
    
    return {
        'molecule': molecule,
        'pubchem': pubchem,
        'wo_discovery': {
            'total_found': len(wo_numbers),
            'processed': len(wo_to_process),
            'successful': len(wo_results)
        },
        'wo_patents': wo_results,
        'br_patents': br_patents,
        'summary': {
            'total_br_patents': len(br_patents),
            'total_wos': len(wo_results),
            'countries': sorted(list(set(
                app['country_code']
                for wo in wo_results
                for apps in wo.get('worldwide_applications', {}).values()
                for app in apps
                if app.get('country_code')
            )))
        }
    }
