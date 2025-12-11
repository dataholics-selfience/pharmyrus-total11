"""
Pipeline Service v3.1 HOTFIX - PRODUCTION
Complete pipeline: PubChem → WO Discovery → WIPO Details → BR Extraction
"""
import asyncio
import logging
import aiohttp
import re
from typing import Dict, Any, List
from .crawler_pool import crawler_pool

logger = logging.getLogger(__name__)

async def _get_pubchem_data(molecule: str) -> Dict:
    """
    Get dev codes and CAS from PubChem
    Returns: {'dev_codes': [...], 'cas': '...'}
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{molecule}/synonyms/JSON"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    syns = data.get('InformationList', {}).get('Information', [{}])[0].get('Synonym', [])
                    
                    # Extract dev codes (e.g., ODM-201, BAY-1841788)
                    dev_codes = []
                    for s in syns:
                        if isinstance(s, str) and len(s) < 20:
                            # Match pattern: 2-5 letters, optional hyphen, 3-7 digits
                            if re.match(r'^[A-Z]{2,5}[-\s]?\d{3,7}[A-Z]?$', s, re.IGNORECASE):
                                if 'CID' not in s.upper():
                                    dev_codes.append(s)
                    
                    dev_codes = dev_codes[:10]  # Limit to 10
                    
                    # Extract CAS number (pattern: XXXXX-XX-X)
                    cas = None
                    for s in syns:
                        if isinstance(s, str) and re.match(r'^\d{2,7}-\d{2}-\d$', s):
                            cas = s
                            break
                    
                    logger.info(f"✅ PubChem: {len(dev_codes)} dev codes, CAS={cas}")
                    
                    return {
                        'dev_codes': dev_codes,
                        'cas': cas
                    }
    
    except Exception as e:
        logger.error(f"❌ PubChem error: {e}")
    
    return {'dev_codes': [], 'cas': None}


async def _discover_wo_numbers(molecule: str, dev_codes: List[str]) -> List[str]:
    """
    Discover WO numbers from multiple Google searches
    
    Strategy:
    - Year-based searches (2011-2024)
    - Dev code searches
    - Company-based searches
    
    Returns: List of unique WO numbers
    """
    wo_numbers = set()
    
    # Build search queries
    queries = []
    
    # 1. Year-based queries (14 queries)
    for year in range(2011, 2025):
        queries.append(f"{molecule} patent WO{year}")
    
    # 2. Dev code queries (up to 5)
    for code in dev_codes[:5]:
        queries.append(f"{code} patent WO")
    
    # 3. Company-based queries
    companies = [
        'Orion Corporation',
        'Bayer',
        'Pfizer',
        'Merck',
        'Novartis',
        'Roche'
    ]
    
    for company in companies[:3]:  # Limit to 3 companies
        queries.append(f"{molecule} {company} patent")
    
    logger.info(f"🔍 Running {len(queries)} parallel WO searches...")
    
    # Search function
    async def search_google(query: str, session: aiohttp.ClientSession):
        """Single Google search via SerpAPI"""
        try:
            # SerpAPI key (NOTE: You should rotate these in production)
            api_key = "3f22448f4d43ce8259fa2f7f6385222323a67c4ce4e72fcc774b43d23812889d"
            
            url = f"https://serpapi.com/search.json?engine=google&q={query}&api_key={api_key}&num=20"
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Extract WO numbers from results
                    results_text = str(data.get('organic_results', []))
                    
                    # Regex: WO followed by year (4 digits) and number (6 digits)
                    # Examples: WO2016168716, WO 2011/051540, WO2011-051540
                    matches = re.findall(
                        r'WO[\s-]?(\d{4})[\s/\-]?(\d{6})',
                        results_text,
                        re.IGNORECASE
                    )
                    
                    for year, number in matches:
                        wo = f"WO{year}{number}"
                        wo_numbers.add(wo)
                    
                    logger.debug(f"  Query '{query[:30]}...' → {len(matches)} WOs")
                
                elif resp.status == 429:
                    logger.warning(f"  Rate limited on query: {query[:30]}...")
                else:
                    logger.debug(f"  Query failed ({resp.status}): {query[:30]}...")
        
        except asyncio.TimeoutError:
            logger.debug(f"  Timeout: {query[:30]}...")
        except Exception as e:
            logger.debug(f"  Error on '{query[:30]}...': {e}")
    
    # Execute all searches in parallel with single session
    try:
        async with aiohttp.ClientSession() as session:
            tasks = [search_google(q, session) for q in queries]
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Search error: {e}")
    
    # Sort and return
    result = sorted(list(wo_numbers))
    
    logger.info(f"✅ Found {len(result)} unique WO numbers")
    
    if len(result) == 0:
        logger.warning("⚠️ NO WO numbers found! Check:")
        logger.warning("  1. SerpAPI rate limits")
        logger.warning("  2. Search query effectiveness")
        logger.warning("  3. Regex pattern matching")
    
    return result


async def _process_wo_batch(wo_numbers: List[str]) -> List[Dict]:
    """
    Process multiple WO numbers in parallel
    
    Args:
        wo_numbers: List of WO numbers to fetch
    
    Returns:
        List of patent dicts (only successful ones)
    """
    
    async def fetch_one(wo: str):
        """Fetch single WO patent"""
        try:
            crawler = crawler_pool.get_crawler()
            result = await crawler.fetch_patent(wo)
            
            # Check if fetch was successful
            if result.get('erro'):
                logger.warning(f"  ⚠️ {wo}: {result['erro']}")
                return None
            
            return result
        
        except Exception as e:
            logger.error(f"  ❌ Error fetching {wo}: {e}")
            return None
    
    # Fetch all in parallel
    logger.info(f"📥 Fetching {len(wo_numbers)} WO patents...")
    
    results = await asyncio.gather(
        *[fetch_one(wo) for wo in wo_numbers],
        return_exceptions=True
    )
    
    # Filter successful results
    valid = []
    for r in results:
        if r is not None and isinstance(r, dict) and not r.get('erro'):
            valid.append(r)
    
    logger.info(f"✅ Processed {len(valid)}/{len(wo_numbers)} WO numbers successfully")
    
    return valid


async def pipeline_search(molecule: str, max_wos: int = 5) -> Dict[str, Any]:
    """
    Full pipeline search
    
    Steps:
    1. Get PubChem data (dev codes, CAS)
    2. Discover WO numbers via multiple Google searches
    3. Fetch detailed WIPO data for each WO
    4. Extract BR patents from worldwide_applications
    
    Args:
        molecule: Molecule name (e.g., "darolutamide")
        max_wos: Maximum WO numbers to process (default: 5)
    
    Returns:
        Complete pipeline result dict
    """
    logger.info(f"🚀 Starting pipeline for: {molecule}")
    
    # Step 1: PubChem
    logger.info("📚 Step 1: Fetching PubChem data...")
    pubchem = await _get_pubchem_data(molecule)
    
    # Step 2: WO Discovery
    logger.info("🔍 Step 2: Discovering WO numbers...")
    wo_numbers = await _discover_wo_numbers(molecule, pubchem['dev_codes'])
    
    # Step 3: Process WOs (limited)
    wo_to_process = wo_numbers[:max_wos]
    
    logger.info(f"⚙️ Step 3: Processing {len(wo_to_process)} WO numbers (limit={max_wos})...")
    
    wo_results = await _process_wo_batch(wo_to_process)
    
    # Step 4: Extract BR patents
    logger.info("🇧🇷 Step 4: Extracting BR patents...")
    
    br_patents = []
    
    for wo in wo_results:
        wo_number = wo.get('publicacao', 'unknown')
        
        for year, apps in wo.get('worldwide_applications', {}).items():
            for app in apps:
                if app.get('country_code') == 'BR':
                    br_patents.append({
                        'wo_number': wo_number,
                        'filing_date': app.get('filing_date', ''),
                        'application_number': app.get('application_number', ''),
                        'legal_status': app.get('legal_status', ''),
                        'year': year,
                        'source': 'WIPO'
                    })
    
    # Build summary
    all_countries = sorted(list(set(
        app['country_code']
        for wo in wo_results
        for apps in wo.get('worldwide_applications', {}).values()
        for app in apps
        if app.get('country_code')
    )))
    
    logger.info(f"✅ Pipeline complete: {len(br_patents)} BR patents from {len(wo_results)} WOs")
    
    # Final result
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
            'countries': all_countries,
            'years': sorted(list(set(p['year'] for p in br_patents)))
        }
    }
