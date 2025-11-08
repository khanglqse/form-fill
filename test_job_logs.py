#!/usr/bin/env python3
"""
Test script to create sample job logs (success and failed) in MongoDB
Run with: python test_job_logs.py
Or in Docker: docker exec -it worker python /path/to/test_job_logs.py
"""
import os
import time
import sys
from pymongo import MongoClient

# Set MongoDB URI if not set (for Docker environment)
if not os.getenv("MONGODB_URI"):
    # Try Docker MongoDB first
    os.environ["MONGODB_URI"] = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/forms")

# Add worker app to path
worker_app_path = os.path.join(os.path.dirname(__file__), 'worker', 'app')
if os.path.exists(worker_app_path):
    sys.path.insert(0, worker_app_path)

# Try different import methods
try:
    # When executed as a package inside Docker: python -m app.main
    from app.job_logger import log_job_start, log_job_success, log_job_failure
except ImportError:
    try:
        # When executed directly: python main.py
        from job_logger import log_job_start, log_job_success, log_job_failure
    except ImportError:
        # Fallback: import from worker app
        import importlib.util
        spec = importlib.util.spec_from_file_location("job_logger", os.path.join(worker_app_path, "job_logger.py"))
        job_logger = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(job_logger)
        log_job_start = job_logger.log_job_start
        log_job_success = job_logger.log_job_success
        log_job_failure = job_logger.log_job_failure


def create_sample_jobs():
    """Create sample job logs for testing"""
    print("🔄 Creating sample job logs...")
    
    # Create successful worker jobs
    print("\n1. Creating successful worker jobs...")
    for i in range(3):
        job_id = f"worker-test-success-{int(time.time())}-{i}"
        metadata = {
            "bucket": "form-files",
            "key": f"raw/test-form-{i}.docx",
            "form_id": f"test-form-{i}",
            "form_title": f"Test Form {i}",
            "fields_count": 5 + i,
            "pages": 1
        }
        
        start_time = time.time()
        log_job_start(
            job_type="worker",
            job_id=job_id,
            metadata=metadata
        )
        
        # Simulate processing time
        time.sleep(0.1)
        
        log_job_success(
            job_type="worker",
            job_id=job_id,
            metadata=metadata,
            start_time=start_time
        )
        
        print(f"  ✅ Created successful worker job: {job_id}")
    
    # Create failed worker jobs
    print("\n2. Creating failed worker jobs...")
    for i in range(2):
        job_id = f"worker-test-failed-{int(time.time())}-{i}"
        metadata = {
            "bucket": "form-files",
            "key": f"raw/failed-form-{i}.docx",
            "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        }
        
        start_time = time.time()
        log_job_start(
            job_type="worker",
            job_id=job_id,
            metadata=metadata
        )
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Simulate different error types
        errors = [
            "File not found in S3 bucket",
            "OCR extraction failed: Unsupported file format"
        ]
        
        try:
            raise Exception(errors[i])
        except Exception as e:
            log_job_failure(
                job_type="worker",
                job_id=job_id,
                error=str(e),
                metadata=metadata,
                start_time=start_time,
                exception=e
            )
        
        print(f"  ❌ Created failed worker job: {job_id}")
    
    # Create successful crawler jobs
    print("\n3. Creating successful crawler jobs...")
    for i in range(2):
        job_id = f"crawler-test-success-{int(time.time())}-{i}"
        metadata = {
            "bucket": "form-files",
            "key": f"raw/topcv-{int(time.time())}-{i}.docx",
            "source_url": "https://static.topcv.vn/cms/19d60037982db4e139cd6b99f3adfefa.docx",
            "s3_path": f"s3://form-files/raw/topcv-{int(time.time())}-{i}.docx",
            "status": "uploaded"
        }
        
        start_time = time.time()
        log_job_start(
            job_type="crawler",
            job_id=job_id,
            metadata=metadata
        )
        
        # Simulate processing time
        time.sleep(0.2)
        
        log_job_success(
            job_type="crawler",
            job_id=job_id,
            metadata=metadata,
            start_time=start_time
        )
        
        print(f"  ✅ Created successful crawler job: {job_id}")
    
    # Create failed crawler jobs
    print("\n4. Creating failed crawler jobs...")
    for i in range(1):
        job_id = f"crawler-test-failed-{int(time.time())}-{i}"
        metadata = {
            "bucket": "form-files",
            "key": f"raw/failed-crawl-{i}.docx",
            "source_url": "https://invalid-url.example.com/file.docx",
            "endpoint": None
        }
        
        start_time = time.time()
        log_job_start(
            job_type="crawler",
            job_id=job_id,
            metadata=metadata
        )
        
        # Simulate processing time
        time.sleep(0.1)
        
        try:
            raise Exception("Failed to download file: Connection timeout")
        except Exception as e:
            log_job_failure(
                job_type="crawler",
                job_id=job_id,
                error=str(e),
                metadata=metadata,
                start_time=start_time,
                exception=e
            )
        
        print(f"  ❌ Created failed crawler job: {job_id}")
    
    # Create running jobs
    print("\n5. Creating running jobs...")
    for i in range(2):
        job_id = f"worker-test-running-{int(time.time())}-{i}"
        metadata = {
            "bucket": "form-files",
            "key": f"raw/processing-form-{i}.docx",
            "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        }
        
        log_job_start(
            job_type="worker",
            job_id=job_id,
            metadata=metadata
        )
        
        print(f"  ⏳ Created running worker job: {job_id}")
    
    print("\n✅ Sample job logs created successfully!")
    print("\nYou can query them using:")
    print("  - GET http://localhost:8000/jobs")
    print("  - GET http://localhost:8000/jobs?status=success")
    print("  - GET http://localhost:8000/jobs?status=failed")
    print("  - GET http://localhost:8000/jobs?job_type=worker")
    print("  - GET http://localhost:8000/jobs/stats/summary")


if __name__ == "__main__":
    try:
        create_sample_jobs()
    except Exception as e:
        print(f"❌ Error creating sample jobs: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

