"""
Locust load testing script for Carpeta Ciudadana

Tests:
- Document upload flow
- Search operations
- P2P transfers

Usage:
    locust -f locustfile.py
    locust -f locustfile.py --host=http://localhost:8000
    locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m
"""

import time
import random
import hashlib
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


class CarpetaCiudadanaUser(FastHttpUser):
    """Simulated user for load testing."""
    
    # Wait time between tasks (1-3 seconds)
    wait_time = between(1, 3)
    
    # Base configuration
    host = "http://localhost:8000"
    
    def on_start(self):
        """Called when a user starts."""
        self.citizen_id = self._generate_citizen_id()
        self.api_key = "test-api-key"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Track uploaded documents
        self.documents = []
    
    def _generate_citizen_id(self):
        """Generate random 10-digit citizen ID."""
        return str(random.randint(1000000000, 9999999999))
    
    def _generate_document_data(self):
        """Generate random document data."""
        timestamp = int(time.time() * 1000)
        return {
            "title": f"Test Document {timestamp}",
            "description": "Load test document",
            "citizenId": self.citizen_id,
            "sha256Hash": hashlib.sha256(str(timestamp).encode()).hexdigest(),
            "sizeBytes": random.randint(1000, 100000),
            "contentType": "application/pdf",
            "filename": f"test_{timestamp}.pdf"
        }
    
    @task(5)
    def upload_document(self):
        """
        Task: Upload document (50% weight)
        
        Flow:
        1. Request upload URL
        2. Upload to presigned URL (simulated)
        3. Confirm upload
        """
        doc_data = self._generate_document_data()
        
        # Step 1: Request upload URL
        with self.client.post(
            "/api/documents/upload-url",
            json={
                "filename": doc_data["filename"],
                "contentType": doc_data["contentType"],
                "citizenId": doc_data["citizenId"]
            },
            headers=self.headers,
            catch_response=True,
            name="/api/documents/upload-url"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                doc_id = data.get("documentId")
                response.success()
                
                # Simulate upload to presigned URL
                time.sleep(0.5)
                
                # Step 2: Confirm upload
                with self.client.post(
                    "/api/documents/confirm-upload",
                    json={
                        "documentId": doc_id,
                        "sha256Hash": doc_data["sha256Hash"],
                        "sizeBytes": doc_data["sizeBytes"]
                    },
                    headers=self.headers,
                    catch_response=True,
                    name="/api/documents/confirm-upload"
                ) as confirm_response:
                    if confirm_response.status_code == 200:
                        self.documents.append(doc_id)
                        confirm_response.success()
                    elif confirm_response.status_code == 429:
                        confirm_response.failure("Rate limit exceeded")
                    else:
                        confirm_response.failure(f"Failed: {confirm_response.status_code}")
            
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(3)
    def search_documents(self):
        """
        Task: Search documents (30% weight)
        """
        queries = [
            "certificado",
            "documento",
            "título",
            "test",
            "identificación"
        ]
        
        query = random.choice(queries)
        
        with self.client.get(
            f"/api/metadata/search?q={query}&limit=20",
            headers=self.headers,
            catch_response=True,
            name="/api/metadata/search"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "documents" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(2)
    def initiate_transfer(self):
        """
        Task: Initiate P2P transfer (20% weight)
        """
        transfer_token = f"transfer_{int(time.time() * 1000)}"
        
        with self.client.post(
            "/api/transferCitizen",
            json={
                "citizenId": self.citizen_id,
                "destinationOperatorId": "operator-test",
                "token": transfer_token
            },
            headers={
                **self.headers,
                "Idempotency-Key": transfer_token
            },
            catch_response=True,
            name="/api/transferCitizen"
        ) as response:
            if response.status_code in [201, 202]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            elif response.status_code == 409:
                # Idempotency key already used
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(1)
    def list_documents(self):
        """
        Task: List user documents (10% weight)
        """
        with self.client.get(
            f"/api/metadata/documents?citizen_id={self.citizen_id}&limit=20",
            headers=self.headers,
            catch_response=True,
            name="/api/metadata/documents"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Failed: {response.status_code}")
    
    @task(1)
    def get_operators(self):
        """
        Task: Get operators list (10% weight)
        """
        with self.client.get(
            "/api/operators",
            headers=self.headers,
            catch_response=True,
            name="/api/operators"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limit exceeded")
            else:
                response.failure(f"Failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "="*50)
    print("Starting Carpeta Ciudadana Load Test")
    print(f"Host: {environment.host}")
    print("="*50 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "="*50)
    print("Load Test Completed")
    print("="*50 + "\n")
    
    # Print summary
    stats = environment.stats
    print("Summary:")
    print(f"  Total requests: {stats.total.num_requests}")
    print(f"  Total failures: {stats.total.num_failures}")
    print(f"  Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"  p95 response time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  p99 response time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    print()

