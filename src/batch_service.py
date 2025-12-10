"""Batch Service v3.1"""
import asyncio
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from .pipeline_service import PipelineService

class BatchService:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.pipeline = PipelineService()
    
    async def process_batch(
        self,
        molecules: List[str],
        country_filter: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        start_time = time.time()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_one(molecule: str):
            async with semaphore:
                try:
                    result = await self.pipeline.execute_full_pipeline(
                        molecule=molecule,
                        country_filter=country_filter,
                        limit=limit
                    )
                    result['molecule'] = molecule
                    result['status'] = 'success'
                    return result
                except Exception as e:
                    return {'molecule': molecule, 'status': 'error', 'error': str(e)}
        
        results = await asyncio.gather(*[process_one(mol) for mol in molecules])
        
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') != 'success']
        
        return {
            "batch_summary": {
                "total_molecules": len(molecules),
                "successful": len(successful),
                "failed": len(failed),
                "duration_seconds": round(time.time() - start_time, 2)
            },
            "results": successful,
            "errors": failed,
            "timestamp": datetime.utcnow().isoformat()
        }
