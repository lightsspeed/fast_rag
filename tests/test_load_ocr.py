"""
Load Testing for OCR Pipeline
Uses Locust to simulate concurrent PDF uploads and queries
"""
from locust import HttpUser, task, between, events
import os
import random
import time
import logging

logger = logging.getLogger(__name__)


class OCRLoadTestUser(HttpUser):
    """
    Simulated user for load testing OCR pipeline
    """
    
    # Wait 1-3 seconds between tasks
    wait_time = between(1, 3)
    
    # Test files directory
    test_files_dir = "uploads"
    
    def on_start(self):
        """Called when a simulated user starts"""
        logger.info(f"Starting load test user: {self.environment.runner.user_count} active")
        
        # List available test PDFs
        self.test_pdfs = []
        if os.path.exists(self.test_files_dir):
            self.test_pdfs = [
                f for f in os.listdir(self.test_files_dir) 
                if f.endswith('.pdf')
            ]
        
        if not self.test_pdfs:
            logger.warning(f"No test PDFs found in {self.test_files_dir}")
    
    @task(3)
    def upload_small_pdf(self):
        """
        Simulate small PDF upload (high frequency)
        Weight: 3 (60% of requests)
        """
        if not self.test_pdfs:
            return
        
        # Select a random test PDF
        pdf_file = random.choice(self.test_pdfs)
        file_path = os.path.join(self.test_files_dir, pdf_file)
        
        try:
            with open(file_path, 'rb') as f:
                files = {'files': (pdf_file, f, 'application/pdf')}
                
                with self.client.post(
                    "/api/documents/upload",
                    files=files,
                    catch_response=True,
                    name="upload_pdf"
                ) as response:
                    if response.status_code == 200:
                        response.success()
                        logger.debug(f"Uploaded {pdf_file}: {response.status_code}")
                    else:
                        response.failure(f"Upload failed: {response.status_code}")
                        
        except Exception as e:
            logger.error(f"Upload error: {e}")
    
    @task(5)
    def query_documents(self):
        """
        Simulate document query (high frequency)
        Weight: 5 (most common operation)
        """
        queries = [
            "Android Enterprise enrollment",
            "error code caa70084",
            "AirWatch configuration",
            "mobile device management",
            "troubleshooting steps"
        ]
        
        query = random.choice(queries)
        
        try:
            with self.client.post(
                "/api/chat",
                json={
                    "query": query,
                    "session_id": f"load_test_{self.environment.runner.user_count}",
                    "user_id": f"test_user_{id(self)}"
                },
                catch_response=True,
                name="query_rag"
            ) as response:
                if response.status_code == 200:
                    response.success()
                    # Verify response has expected structure
                    data = response.json()
                    if 'answer' not in data:
                        response.failure("Response missing 'answer' field")
                else:
                    response.failure(f"Query failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Query error: {e}")
    
    @task(1)
    def list_documents(self):
        """
        Simulate listing documents (low frequency)
        Weight: 1 (20% of requests)
        """
        try:
            with self.client.get(
                "/api/documents",
                catch_response=True,
                name="list_documents"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"List failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"List error: {e}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("\n" + "="*80)
    print("LOAD TEST STARTING")
    print("="*80)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("\n" + "="*80)
    print("LOAD TEST COMPLETED")
    print("="*80)
    
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"RPS: {stats.total.total_rps:.2f}")
    print(f"P95 latency: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 latency: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print("="*80 + "\n")


# Run with:
# locust -f tests/test_load_ocr.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=5m
