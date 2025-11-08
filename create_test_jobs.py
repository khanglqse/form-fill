#!/usr/bin/env python3
"""
Simple script to create test job logs directly in MongoDB
Run with: docker exec -it mongodb mongosh forms --eval "$(cat create_test_jobs.js)"
Or: python create_test_jobs.py (if MongoDB is accessible)
"""
import os
import time
from pymongo import MongoClient

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/forms")
client = MongoClient(MONGODB_URI)

# Get database
if "/" in MONGODB_URI.split("mongodb://")[-1]:
    db = client.get_default_database()
else:
    db = client["forms"]

print("🔄 Creating sample job logs in MongoDB...")

# Create successful worker jobs
print("\n1. Creating successful worker jobs...")
for i in range(3):
    job_id = f"worker-test-success-{int(time.time())}-{i}"
    start_time = time.time() - 10  # 10 seconds ago
    end_time = time.time()
    duration = end_time - start_time
    
    job_doc = {
        "job_type": "worker",
        "job_id": job_id,
        "status": "success",
        "metadata": {
            "bucket": "form-files",
            "key": f"raw/test-form-{i}.docx",
            "form_id": f"test-form-{i}",
            "form_title": f"Test Form {i}",
            "fields_count": 5 + i,
            "pages": 1
        },
        "duration_seconds": round(duration, 2),
        "start_time": start_time,
        "end_time": end_time,
        "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time)),
        "created_at": int(start_time),
        "updated_at": int(end_time)
    }
    
    db.jobs.update_one(
        {"job_type": "worker", "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    print(f"  ✅ Created successful worker job: {job_id}")

# Create failed worker jobs
print("\n2. Creating failed worker jobs...")
for i in range(2):
    job_id = f"worker-test-failed-{int(time.time())}-{i}"
    start_time = time.time() - 5
    end_time = time.time()
    duration = end_time - start_time
    
    errors = [
        "File not found in S3 bucket",
        "OCR extraction failed: Unsupported file format"
    ]
    
    job_doc = {
        "job_type": "worker",
        "job_id": job_id,
        "status": "failed",
        "metadata": {
            "bucket": "form-files",
            "key": f"raw/failed-form-{i}.docx",
            "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        },
        "error": errors[i],
        "error_traceback": f"Traceback (most recent call last):\n  File \"worker/app/main.py\", line 110\n    raise Exception(\"{errors[i]}\")\nException: {errors[i]}",
        "duration_seconds": round(duration, 2),
        "start_time": start_time,
        "end_time": end_time,
        "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time)),
        "created_at": int(start_time),
        "updated_at": int(end_time)
    }
    
    db.jobs.update_one(
        {"job_type": "worker", "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    print(f"  ❌ Created failed worker job: {job_id}")

# Create successful crawler jobs
print("\n3. Creating successful crawler jobs...")
for i in range(2):
    job_id = f"crawler-test-success-{int(time.time())}-{i}"
    start_time = time.time() - 15
    end_time = time.time()
    duration = end_time - start_time
    
    job_doc = {
        "job_type": "crawler",
        "job_id": job_id,
        "status": "success",
        "metadata": {
            "bucket": "form-files",
            "key": f"raw/topcv-{int(time.time())}-{i}.docx",
            "source_url": "https://static.topcv.vn/cms/19d60037982db4e139cd6b99f3adfefa.docx",
            "s3_path": f"s3://form-files/raw/topcv-{int(time.time())}-{i}.docx",
            "status": "uploaded"
        },
        "duration_seconds": round(duration, 2),
        "start_time": start_time,
        "end_time": end_time,
        "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time)),
        "created_at": int(start_time),
        "updated_at": int(end_time)
    }
    
    db.jobs.update_one(
        {"job_type": "crawler", "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    print(f"  ✅ Created successful crawler job: {job_id}")

# Create failed crawler jobs
print("\n4. Creating failed crawler jobs...")
for i in range(1):
    job_id = f"crawler-test-failed-{int(time.time())}-{i}"
    start_time = time.time() - 8
    end_time = time.time()
    duration = end_time - start_time
    
    job_doc = {
        "job_type": "crawler",
        "job_id": job_id,
        "status": "failed",
        "metadata": {
            "bucket": "form-files",
            "key": f"raw/failed-crawl-{i}.docx",
            "source_url": "https://invalid-url.example.com/file.docx",
            "endpoint": None
        },
        "error": "Failed to download file: Connection timeout",
        "error_traceback": "Traceback (most recent call last):\n  File \"crawler/app/main.py\", line 84\n    upload_doc_from_url(bucket, key, endpoint)\n  File \"crawler/app/main.py\", line 32\n    resp.raise_for_status()\nrequests.exceptions.Timeout: Connection timeout",
        "duration_seconds": round(duration, 2),
        "start_time": start_time,
        "end_time": end_time,
        "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "end_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time)),
        "created_at": int(start_time),
        "updated_at": int(end_time)
    }
    
    db.jobs.update_one(
        {"job_type": "crawler", "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    print(f"  ❌ Created failed crawler job: {job_id}")

# Create running jobs
print("\n5. Creating running jobs...")
for i in range(2):
    job_id = f"worker-test-running-{int(time.time())}-{i}"
    start_time = time.time()
    
    job_doc = {
        "job_type": "worker",
        "job_id": job_id,
        "status": "running",
        "metadata": {
            "bucket": "form-files",
            "key": f"raw/processing-form-{i}.docx",
            "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
        },
        "start_time": start_time,
        "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "created_at": int(start_time),
        "updated_at": int(start_time)
    }
    
    db.jobs.update_one(
        {"job_type": "worker", "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    print(f"  ⏳ Created running worker job: {job_id}")

print("\n✅ Sample job logs created successfully!")
print("\nYou can query them using:")
print("  - GET http://localhost:8000/jobs")
print("  - GET http://localhost:8000/jobs?status=success")
print("  - GET http://localhost:8000/jobs?status=failed")
print("  - GET http://localhost:8000/jobs?job_type=worker")
print("  - GET http://localhost:8000/jobs/stats/summary")

# Print summary
total = db.jobs.count_documents({})
success = db.jobs.count_documents({"status": "success"})
failed = db.jobs.count_documents({"status": "failed"})
running = db.jobs.count_documents({"status": "running"})

print(f"\n📊 Summary:")
print(f"  Total jobs: {total}")
print(f"  Success: {success}")
print(f"  Failed: {failed}")
print(f"  Running: {running}")

