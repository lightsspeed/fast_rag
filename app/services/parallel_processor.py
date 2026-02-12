"""
Parallel Processing for OCR Pipeline
Processes multiple images concurrently for 4x speedup
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import logging
import time

logger = logging.getLogger(__name__)


class ParallelOCRProcessor:
    """
    Parallel OCR processing manager
    Uses thread pool for I/O-bound OCR operations
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel processor
        
        Args:
            max_workers: Maximum number of concurrent workers (default: 4)
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Initialized ParallelOCRProcessor with {max_workers} workers")
    
    def process_images_parallel(
        self, 
        images_data: List[Dict], 
        processor_func,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Process multiple images in parallel
        
        Args:
            images_data: List of image dictionaries with 'bytes', 'page', 'id', etc.
            processor_func: Function to process each image (takes image_dict, returns result)
            show_progress: Whether to log progress
            
        Returns:
            List of processed results in original order
        """
        total = len(images_data)
        logger.info(f"Starting parallel OCR processing for {total} images with {self.max_workers} workers")
        start_time = time.time()
        
        # Submit all tasks
        future_to_index = {}
        for idx, img_data in enumerate(images_data):
            future = self.executor.submit(processor_func, img_data)
            future_to_index[future] = idx
        
        # Collect results as they complete
        results = [None] * total
        completed = 0
        
        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                results[idx] = result
                completed += 1
                
                if show_progress and completed % 5 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {completed}/{total} images ({completed/total*100:.1f}%) - {rate:.1f} img/sec")
                    
            except Exception as e:
                logger.error(f"Image {idx} processing failed: {e}")
                results[idx] = {
                    "error": str(e),
                    "status": "failed",
                    "index": idx
                }
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r and not r.get('error'))
        
        logger.info(f"Parallel processing complete: {success_count}/{total} successful in {elapsed:.2f}s ({total/elapsed:.1f} img/sec)")
        
        return results
    
    async def process_images_async(
        self,
        images_data: List[Dict],
        processor_func,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Async variant of parallel processing
        
        Args:
            images_data: List of image dictionaries
            processor_func: Sync function to process each image
            show_progress: Whether to log progress
            
        Returns:
            List of processed results
        """
        loop = asyncio.get_event_loop()
        total = len(images_data)
        
        logger.info(f"Starting async parallel OCR for {total} images")
        start_time = time.time()
        
        # Create tasks
        tasks = [
            loop.run_in_executor(self.executor, processor_func, img_data)
            for img_data in images_data
        ]
        
        # Execute with progress tracking
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                
                if show_progress and (i + 1) % 5 == 0:
                    elapsed = time.time() - start_time
                    logger.info(f"Progress: {i+1}/{total} images ({(i+1)/total*100:.1f}%)")
                    
            except Exception as e:
                logger.error(f"Image {i} processing failed: {e}")
                results.append({"error": str(e), "status": "failed"})
        
        elapsed = time.time() - start_time
        logger.info(f"Async processing complete in {elapsed:.2f}s ({total/elapsed:.1f} img/sec)")
        
        return results
    
    def shutdown(self):
        """Gracefully shutdown executor"""
        self.executor.shutdown(wait=True)
        logger.info("ParallelOCRProcessor shutdown complete")


# Global instance
parallel_ocr_processor = ParallelOCRProcessor(max_workers=4)
