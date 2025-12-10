"""
Batch Service v3.1 - Process multiple molecules in parallel
"""
import asyncio
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
from .pipeline_service import PipelineService
import logging

logger = logging.getLogger(__name__)

class BatchService:
    """Batch processing service for multiple molecules"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.pipeline = PipelineService()
    
    async def process_batch(
        self,
        molecules: List[str],
        country_filter: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Process multiple molecules in parallel with concurrency control
        """
        start_time = time.time()
        
        logger.info(f"📦 Batch processing {len(molecules)} molecules (max {self.max_concurrent} concurrent)")
        
        results = []
        errors = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_one(molecule: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    logger.info(f"🔍 Processing: {molecule}")
                    result = await self.pipeline.execute_full_pipeline(
                        molecule=molecule,
                        country_filter=country_filter,
                        limit=limit
                    )
                    result['molecule'] = molecule
                    result['status'] = 'success'
                    return result
                except Exception as e:
                    logger.error(f"❌ Error processing {molecule}: {e}")
                    return {
                        'molecule': molecule,
                        'status': 'error',
                        'error': str(e)
                    }
        
        # Process all molecules
        tasks = [process_one(mol) for mol in molecules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successes and errors
        successful = []
        failed = []
        
        for result in results:
            if isinstance(result, Exception):
                failed.append({'error': str(result), 'status': 'exception'})
            elif result.get('status') == 'error':
                failed.append(result)
            else:
                successful.append(result)
        
        duration = time.time() - start_time
        
        return {
            "batch_summary": {
                "total_molecules": len(molecules),
                "successful": len(successful),
                "failed": len(failed),
                "duration_seconds": round(duration, 2),
                "average_per_molecule": round(duration / len(molecules), 2) if molecules else 0
            },
            "results": successful,
            "errors": failed,
            "timestamp": datetime.utcnow().isoformat()
        }
