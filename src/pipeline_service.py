"""
Pipeline Service v3.1 HOTFIX - Complete Patent Intelligence Pipeline
CORREÇÕES:
- WO discovery corrigido com múltiplas fontes
- Integração com WIPO crawler local (não mais chamada externa)
- Debug detalhado em camadas
- Extração completa de worldwide applications
"""
import asyncio
import aiohttp
import time
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from .wipo_crawler import WIPOCrawler
import logging

logger = logging.getLogger(__name__)

class PipelineService:
    """Orchestrates complete patent search pipeline"""
    
    def __init__(self):
        self.serp_api_key = "3f22448f4d43ce8259fa2f7f6385222323a67c4ce4e72fcc774b43d23812889d"
        self.inpi_api = "https://crawler3-production.up.railway.app/api/data/inpi/patents"
        self.fda_api = "https://api.fda.gov/drug"
        self.clinical_trials_api = "https://clinicaltrials.gov/api/v2/studies"
        self.pubchem_api = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        
    async def execute_full_pipeline(
        self,
        molecule: str,
        country_filter: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Execute complete 6-layer pipeline with parallel processing"""
        
        start_time = time.time()
        debug_layers = []
        
        # Layer 1: PubChem
        layer1_start = time.time()
        pubchem_data = await self._layer1_pubchem(molecule)
        layer1_duration = time.time() - layer1_start
        debug_layers.append({
            "layer": "Layer 1: PubChem",
            "status": "success" if pubchem_data.get("cid") else "partial",
            "duration_seconds": round(layer1_duration, 2),
            "data_points": len(pubchem_data.get("synonyms", [])),
            "details": f"Found {len(pubchem_data.get('dev_codes', []))} dev codes, {len(pubchem_data.get('synonyms', []))} synonyms"
        })
        
        # Layer 2: WO Discovery (CORRIGIDO!)
        layer2_start = time.time()
        wo_numbers = await self._layer2_discover_wos(molecule, pubchem_data)
        layer2_duration = time.time() - layer2_start
        debug_layers.append({
            "layer": "Layer 2: WO Discovery",
            "status": "success" if wo_numbers else "no_results",
            "duration_seconds": round(layer2_duration, 2),
            "data_points": len(wo_numbers),
            "details": f"Found {len(wo_numbers)} WO patents from parallel queries"
        })
        
        wo_numbers_limited = wo_numbers[:limit]
        
        # Layers 3-6: Parallel execution
        layer3_start = time.time()
        
        results = await asyncio.gather(
            self._layer3_patent_details(wo_numbers_limited, country_filter),
            self._layer4_inpi_brasil(molecule, pubchem_data),
            self._layer5_fda_data(molecule),
            self._layer6_clinical_trials(molecule),
            return_exceptions=True
        )
        
        patent_details, inpi_patents, fda_data, clinical_data = results
        layer3_duration = time.time() - layer3_start
        
        # Debug layers 3-6
        if isinstance(patent_details, Exception):
            patent_details = {"patents": [], "errors": [str(patent_details)]}
        debug_layers.append({
            "layer": "Layer 3: Patent Details",
            "status": "success" if patent_details.get("patents") else "no_results",
            "duration_seconds": round(layer3_duration, 2),
            "data_points": len(patent_details.get("patents", [])),
            "details": f"Processed {len(wo_numbers_limited)} WO patents with worldwide data"
        })
        
        if isinstance(inpi_patents, Exception):
            inpi_patents = {"br_patents": [], "errors": [str(inpi_patents)]}
        debug_layers.append({
            "layer": "Layer 4: INPI Brasil",
            "status": "success" if inpi_patents.get("br_patents") else "no_results",
            "duration_seconds": round(layer3_duration, 2),
            "data_points": len(inpi_patents.get("br_patents", [])),
            "details": f"Found {len(inpi_patents.get('br_patents', []))} BR patents"
        })
        
        if isinstance(fda_data, Exception):
            fda_data = {"approval_status": "Error", "errors": [str(fda_data)]}
        debug_layers.append({
            "layer": "Layer 5: FDA",
            "status": "success" if fda_data.get("approval_status") != "Error" else "error",
            "duration_seconds": round(layer3_duration, 2),
            "data_points": len(fda_data.get("applications", [])),
            "details": f"FDA Status: {fda_data.get('approval_status', 'Unknown')}"
        })
        
        if isinstance(clinical_data, Exception):
            clinical_data = {"total_trials": 0, "errors": [str(clinical_data)]}
        debug_layers.append({
            "layer": "Layer 6: Clinical Trials",
            "status": "success" if clinical_data.get("total_trials", 0) > 0 else "no_results",
            "duration_seconds": round(layer3_duration, 2),
            "data_points": clinical_data.get("total_trials", 0),
            "details": f"Found {clinical_data.get('total_trials', 0)} clinical trials"
        })
        
        all_patents = self._aggregate_patents(patent_details, inpi_patents)
        
        total_duration = time.time() - start_time
        executive_summary = self._build_executive_summary(
            molecule,
            pubchem_data,
            all_patents,
            fda_data,
            clinical_data
        )
        
        response = {
            "executive_summary": executive_summary,
            "pubchem_data": pubchem_data,
            "search_strategy": {
                "pipeline_version": "3.1-HOTFIX",
                "execution_mode": "parallel_batch",
                "layers_executed": ["PubChem", "Google Patents", "WIPO", "INPI", "FDA", "ClinicalTrials"],
                "total_wo_patents": len(wo_numbers),
                "wo_patents_processed": len(wo_numbers_limited),
                "country_filter": country_filter or "ALL",
                "parallel_processing": True,
                "sources": {
                    "pubchem": "NIH PubChem API",
                    "google_patents": "SerpAPI Google Patents",
                    "wipo": "WIPO Patentscope Crawler (local)",
                    "inpi": "INPI Brasil API",
                    "fda": "FDA API",
                    "clinical_trials": "ClinicalTrials.gov API v2"
                }
            },
            "wo_patents": patent_details.get("patents", []),
            "br_patents_inpi": inpi_patents.get("br_patents", []),
            "all_patents": all_patents,
            "fda_data": fda_data,
            "clinical_trials_data": clinical_data,
            "debug_info": {
                "total_duration_seconds": round(total_duration, 2),
                "layers": debug_layers,
                "timings": {
                    "pubchem": round(layer1_duration, 2),
                    "wo_discovery": round(layer2_duration, 2),
                    "parallel_batch": round(layer3_duration, 2),
                    "total": round(total_duration, 2)
                },
                "errors_count": sum(1 for layer in debug_layers if layer["status"] == "error"),
                "warnings_count": sum(1 for layer in debug_layers if layer["status"] in ["partial", "no_results"]),
                "errors": [],
                "warnings": []
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return response
    
    async def _layer1_pubchem(self, molecule: str) -> Dict[str, Any]:
        """Layer 1: Fetch PubChem data"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.pubchem_api}/compound/name/{molecule}/synonyms/JSON"
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        return {"error": "PubChem not found"}
                    
                    data = await resp.json()
                    synonyms = data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
                    
                    dev_codes = []
                    cas_number = None
                    
                    dev_pattern = re.compile(r'^[A-Z]{2,5}-?\d{3,7}[A-Z]?$', re.I)
                    cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
                    
                    for syn in synonyms[:100]:
                        if dev_pattern.match(syn) and len(dev_codes) < 20:
                            dev_codes.append(syn)
                        if cas_pattern.match(syn) and not cas_number:
                            cas_number = syn
                    
                    cid_url = f"{self.pubchem_api}/compound/name/{molecule}/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES,InChI,InChIKey/JSON"
                    properties = {}
                    try:
                        async with session.get(cid_url, timeout=30) as prop_resp:
                            if prop_resp.status == 200:
                                prop_data = await prop_resp.json()
                                props = prop_data.get("PropertyTable", {}).get("Properties", [{}])[0]
                                properties = {
                                    "cid": props.get("CID"),
                                    "molecular_formula": props.get("MolecularFormula"),
                                    "molecular_weight": props.get("MolecularWeight"),
                                    "iupac_name": props.get("IUPACName"),
                                    "canonical_smiles": props.get("CanonicalSMILES"),
                                    "inchi": props.get("InChI"),
                                    "inchi_key": props.get("InChIKey")
                                }
                    except:
                        pass
                    
                    return {
                        "cid": properties.get("cid"),
                        "synonyms": synonyms[:50],
                        "dev_codes": dev_codes,
                        "cas_number": cas_number,
                        **properties
                    }
        except Exception as e:
            return {"error": str(e), "synonyms": [], "dev_codes": []}
    
    async def _layer2_discover_wos(self, molecule: str, pubchem_data: Dict) -> List[str]:
        """
        Layer 2: Discover WO patent numbers (CORRIGIDO!)
        Usa múltiplas fontes paralelas
        """
        
        queries = []
        
        # Queries por ano (2011-2024)
        for year in range(2011, 2025):
            queries.append(f"{molecule} patent WO{year}")
        
        # Dev code queries
        for dev_code in pubchem_data.get("dev_codes", [])[:5]:
            queries.append(f"{dev_code} patent WO")
            queries.append(f'"{dev_code}" WO patent')
        
        # Company queries
        queries.extend([
            f"{molecule} Orion Corporation patent",
            f"{molecule} Bayer patent",
            f'"{molecule}" pharmaceutical patent WO',
            f'"{molecule}" compound patent WO'
        ])
        
        # Execute parallel searches
        logger.info(f"🔎 Executando {len(queries)} queries paralelas para WO discovery...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for query in queries[:20]:  # Limit to 20
                url = f"https://serpapi.com/search.json"
                params = {
                    "engine": "google",
                    "q": query,
                    "api_key": self.serp_api_key,
                    "num": 10
                }
                tasks.append(self._fetch_search(session, url, params))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Extract WO numbers with better regex
        wo_pattern = re.compile(r'WO[\s-]?(\d{4})[\s/]?(\d{6})', re.I)
        wo_numbers = set()
        
        for result in results:
            if isinstance(result, dict):
                for item in result.get("organic_results", []):
                    text = f"{item.get('title', '')} {item.get('snippet', '')} {item.get('link', '')}"
                    matches = wo_pattern.findall(text)
                    for year, num in matches:
                        wo_numbers.add(f"WO{year}{num}")
        
        wo_list = sorted(list(wo_numbers))
        logger.info(f"✅ Descobriu {len(wo_list)} WO numbers únicos")
        
        return wo_list
    
    async def _fetch_search(self, session: aiohttp.ClientSession, url: str, params: Dict) -> Dict:
        """Helper to fetch search results"""
        try:
            async with session.get(url, params=params, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except:
            return {}
    
    async def _layer3_patent_details(self, wo_numbers: List[str], country_filter: Optional[str]) -> Dict:
        """
        Layer 3: Fetch detailed patent information (CORRIGIDO!)
        Usa WIPO crawler LOCAL em vez de chamada externa
        """
        
        if not wo_numbers:
            return {"patents": [], "errors": []}
        
        logger.info(f"📄 Buscando detalhes de {len(wo_numbers)} patentes WO...")
        
        patents = []
        errors = []
        
        # Usa WIPO crawler local
        async with WIPOCrawler(max_retries=3, timeout=60000, headless=True) as crawler:
            for wo in wo_numbers:
                try:
                    logger.info(f"🔍 Processando {wo}...")
                    patent_data = await crawler.fetch_patent(wo)
                    
                    if patent_data.get('erro'):
                        errors.append(f"{wo}: {patent_data.get('erro')}")
                    else:
                        # Filtra por país se solicitado
                        if country_filter:
                            if country_filter in patent_data.get('paises_familia', []):
                                patents.append(patent_data)
                            else:
                                logger.info(f"⏭️  {wo} não tem aplicações em {country_filter}")
                        else:
                            patents.append(patent_data)
                        
                        logger.info(f"✅ {wo}: {len(patent_data.get('worldwide_applications', {}))} aplicações worldwide")
                    
                except Exception as e:
                    logger.error(f"❌ Erro em {wo}: {e}")
                    errors.append(f"{wo}: {str(e)}")
        
        return {
            "patents": patents,
            "errors": errors
        }
    
    async def _layer4_inpi_brasil(self, molecule: str, pubchem_data: Dict) -> Dict:
        """Layer 4: Search INPI Brasil"""
        
        br_patents = []
        errors = []
        
        queries = [molecule]
        queries.extend(pubchem_data.get("dev_codes", [])[:5])
        
        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    url = f"{self.inpi_api}?medicine={query}"
                    async with session.get(url, timeout=60) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            patents = data.get("data", [])
                            for p in patents:
                                if p.get("title", "").startswith("BR"):
                                    br_patents.append({
                                        "number": p.get("title", "").replace(" ", "-"),
                                        "title": p.get("applicant", ""),
                                        "filing_date": p.get("depositDate", ""),
                                        "source": "inpi_direct",
                                        "link": f"https://busca.inpi.gov.br/pePI/servlet/PatenteServletController?Action=detail&CodPedido={p.get('title', '')}"
                                    })
                except Exception as e:
                    errors.append(f"INPI {query}: {str(e)}")
        
        return {
            "br_patents": br_patents,
            "errors": errors
        }
    
    async def _layer5_fda_data(self, molecule: str) -> Dict:
        """Layer 5: Fetch FDA data"""
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.fda_api}/ndc.json?search=generic_name:\"{molecule}\""
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        
                        applications = []
                        for r in results[:10]:
                            applications.append({
                                "product_ndc": r.get("product_ndc"),
                                "brand_name": r.get("brand_name"),
                                "generic_name": r.get("generic_name"),
                                "labeler_name": r.get("labeler_name"),
                                "dosage_form": r.get("dosage_form"),
                                "route": r.get("route", []),
                                "marketing_category": r.get("marketing_category"),
                                "application_number": r.get("application_number")
                            })
                        
                        return {
                            "approval_status": "Approved" if applications else "Not Found",
                            "applications": applications,
                            "total_products": len(results)
                        }
            
            return {"approval_status": "Not Found", "applications": [], "total_products": 0}
            
        except Exception as e:
            return {"approval_status": "Error", "error": str(e), "applications": []}
    
    async def _layer6_clinical_trials(self, molecule: str) -> Dict:
        """Layer 6: Fetch Clinical Trials data"""
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.clinical_trials_api}?query.term={molecule}&pageSize=100"
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        studies = data.get("studies", [])
                        
                        by_phase = {}
                        by_status = {}
                        sponsors = set()
                        countries = set()
                        
                        trial_details = []
                        
                        for study in studies[:20]:
                            proto = study.get("protocolSection", {})
                            ident = proto.get("identificationModule", {})
                            status_mod = proto.get("statusModule", {})
                            design = proto.get("designModule", {})
                            sponsor = proto.get("sponsorCollaboratorsModule", {})
                            location = proto.get("contactsLocationsModule", {})
                            
                            phase = design.get("phases", ["Unknown"])[0] if design.get("phases") else "Unknown"
                            status = status_mod.get("overallStatus", "Unknown")
                            
                            by_phase[phase] = by_phase.get(phase, 0) + 1
                            by_status[status] = by_status.get(status, 0) + 1
                            
                            lead_sponsor = sponsor.get("leadSponsor", {}).get("name")
                            if lead_sponsor:
                                sponsors.add(lead_sponsor)
                            
                            for loc in location.get("locations", []):
                                country = loc.get("country")
                                if country:
                                    countries.add(country)
                            
                            trial_details.append({
                                "nct_id": ident.get("nctId"),
                                "title": ident.get("briefTitle"),
                                "phase": phase,
                                "status": status,
                                "enrollment": status_mod.get("enrollmentInfo", {}).get("count"),
                                "start_date": status_mod.get("startDateStruct", {}).get("date"),
                                "primary_sponsor": lead_sponsor
                            })
                        
                        return {
                            "total_trials": len(studies),
                            "by_phase": by_phase,
                            "by_status": by_status,
                            "sponsors": sorted(list(sponsors)),
                            "countries": sorted(list(countries)),
                            "trial_details": trial_details
                        }
            
            return {"total_trials": 0}
            
        except Exception as e:
            return {"total_trials": 0, "error": str(e)}
    
    def _aggregate_patents(self, patent_details: Dict, inpi_patents: Dict) -> List[Dict]:
        """Aggregate all patents from different sources"""
        
        all_patents = []
        seen = set()
        
        # From WO patents (worldwide applications)
        for patent in patent_details.get("patents", []):
            wo_num = patent.get("publicacao")
            if wo_num and wo_num not in seen:
                seen.add(wo_num)
                all_patents.append({
                    "number": wo_num,
                    "type": "WO",
                    "title": patent.get("titulo"),
                    "applicant": patent.get("titular"),
                    "filing_date": patent.get("datas", {}).get("deposito"),
                    "source": "wipo",
                    "worldwide_apps": len(patent.get("worldwide_applications", {})),
                    "countries": patent.get("paises_familia", [])
                })
        
        # From INPI direct
        for patent in inpi_patents.get("br_patents", []):
            num = patent.get("number")
            if num and num not in seen:
                seen.add(num)
                all_patents.append({
                    "number": num,
                    "type": "BR",
                    "title": patent.get("title"),
                    "filing_date": patent.get("filing_date"),
                    "source": "inpi",
                    "link": patent.get("link")
                })
        
        return all_patents
    
    def _build_executive_summary(
        self,
        molecule: str,
        pubchem_data: Dict,
        all_patents: List[Dict],
        fda_data: Dict,
        clinical_data: Dict
    ) -> Dict:
        """Build executive summary"""
        
        jurisdictions = {
            "brazil": sum(1 for p in all_patents if p.get("type") == "BR" or "BR" in p.get("countries", [])),
            "usa": sum(1 for p in all_patents if "US" in p.get("countries", [])),
            "europe": sum(1 for p in all_patents if "EP" in p.get("countries", [])),
            "japan": sum(1 for p in all_patents if "JP" in p.get("countries", [])),
            "china": sum(1 for p in all_patents if "CN" in p.get("countries", [])),
            "wipo": sum(1 for p in all_patents if p.get("type") == "WO")
        }
        
        return {
            "molecule_name": molecule,
            "generic_name": pubchem_data.get("iupac_name", "")[:100],
            "commercial_name": molecule.title(),
            "cas_number": pubchem_data.get("cas_number"),
            "dev_codes": pubchem_data.get("dev_codes", []),
            "total_patents": len(all_patents),
            "total_families": len(set(p.get("number") for p in all_patents if p.get("number"))),
            "jurisdictions": jurisdictions,
            "fda_status": fda_data.get("approval_status", "Unknown"),
            "clinical_trials_count": clinical_data.get("total_trials", 0),
            "consistency_score": 1 if all_patents else 0
        }
