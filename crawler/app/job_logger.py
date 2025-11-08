"""
Job Logger Module
Logs job execution details to MongoDB for tracking and monitoring
"""
import time
import traceback
from typing import Any, Dict, Optional
from pymongo import MongoClient


def get_mongo_client():
    """Get MongoDB client"""
    import os
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/forms")
    return MongoClient(uri)


def get_db():
    """Get database instance"""
    import os
    client = get_mongo_client()
    if "/" in os.getenv("MONGODB_URI", ""):
        return client.get_default_database()
    return client["forms"]


def log_job(
    job_type: str,
    job_id: str,
    status: str,
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    error_traceback: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> str:
    """
    Log a job execution to MongoDB
    
    Args:
        job_type: Type of job ('worker', 'crawler', etc.)
        job_id: Unique identifier for the job
        status: Job status ('success', 'failed', 'running')
        metadata: Additional job metadata (bucket, key, form_id, etc.)
        error: Error message if job failed
        error_traceback: Full error traceback if job failed
        duration_seconds: Job execution duration in seconds
        start_time: Job start timestamp
        end_time: Job end timestamp
    
    Returns:
        MongoDB document ID
    """
    db = get_db()
    
    # Prepare job document
    job_doc = {
        "job_type": job_type,
        "job_id": job_id,
        "status": status,
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    
    if metadata:
        job_doc["metadata"] = metadata
    
    if error:
        job_doc["error"] = error
    
    if error_traceback:
        job_doc["error_traceback"] = error_traceback
    
    if duration_seconds is not None:
        job_doc["duration_seconds"] = duration_seconds
    
    if start_time:
        job_doc["start_time"] = start_time
        job_doc["start_time_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time))
    
    if end_time:
        job_doc["end_time"] = end_time
        job_doc["end_time_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(end_time))
    
    # Insert or update job log
    result = db.jobs.update_one(
        {"job_type": job_type, "job_id": job_id},
        {"$set": job_doc},
        upsert=True
    )
    
    return str(result.upserted_id) if result.upserted_id else job_id


def log_job_start(
    job_type: str,
    job_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log job start
    
    Args:
        job_type: Type of job
        job_id: Unique job identifier
        metadata: Job metadata
    
    Returns:
        Job log ID
    """
    start_time = time.time()
    return log_job(
        job_type=job_type,
        job_id=job_id,
        status="running",
        metadata=metadata,
        start_time=start_time
    )


def log_job_success(
    job_type: str,
    job_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    start_time: Optional[float] = None
) -> str:
    """
    Log job success
    
    Args:
        job_type: Type of job
        job_id: Unique job identifier
        metadata: Updated job metadata
        start_time: Job start time to calculate duration
    
    Returns:
        Job log ID
    """
    end_time = time.time()
    duration = None
    if start_time:
        duration = end_time - start_time
    
    return log_job(
        job_type=job_type,
        job_id=job_id,
        status="success",
        metadata=metadata,
        duration_seconds=duration,
        start_time=start_time,
        end_time=end_time
    )


def log_job_failure(
    job_type: str,
    job_id: str,
    error: str,
    metadata: Optional[Dict[str, Any]] = None,
    start_time: Optional[float] = None,
    exception: Optional[Exception] = None
) -> str:
    """
    Log job failure
    
    Args:
        job_type: Type of job
        job_id: Unique job identifier
        error: Error message
        metadata: Updated job metadata
        start_time: Job start time to calculate duration
        exception: Exception object to extract traceback
    
    Returns:
        Job log ID
    """
    end_time = time.time()
    duration = None
    if start_time:
        duration = end_time - start_time
    
    error_traceback = None
    if exception:
        error_traceback = traceback.format_exc()
    
    return log_job(
        job_type=job_type,
        job_id=job_id,
        status="failed",
        metadata=metadata,
        error=error,
        error_traceback=error_traceback,
        duration_seconds=duration,
        start_time=start_time,
        end_time=end_time
    )

