import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase


async def aggregate_form_statistics(db: AsyncIOMotorDatabase, form_id: str) -> Dict[str, Any]:
    """Aggregate statistics for a specific form"""
    # Count total sessions
    total_sessions = await db.sessions.count_documents({"formId": form_id})
    
    # Count completed sessions (sessions with all required fields)
    form = await db.forms.find_one({"id": form_id}, {"_id": 0})
    if not form:
        return {}
    
    required_fields = [f["id"] for f in form.get("fields", []) if f.get("required", False)]
    completed_sessions = 0
    total_answers = 0
    field_answer_counts = {}
    
    async for session in db.sessions.find({"formId": form_id}):
        answers = session.get("answers", {})
        total_answers += len(answers)
        
        # Count answers per field
        for field_id, value in answers.items():
            field_answer_counts[field_id] = field_answer_counts.get(field_id, 0) + 1
        
        # Check if completed
        if required_fields:
            if all(field_id in answers for field_id in required_fields):
                completed_sessions += 1
        elif len(answers) > 0:
            completed_sessions += 1
    
    # Calculate completion rate
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Get field popularity
    field_popularity = []
    for field in form.get("fields", []):
        field_id = field.get("id")
        answer_count = field_answer_counts.get(field_id, 0)
        field_popularity.append({
            "field_id": field_id,
            "label": field.get("label", field_id),
            "answer_count": answer_count,
            "popularity_score": (answer_count / total_sessions * 100) if total_sessions > 0 else 0
        })
    field_popularity.sort(key=lambda x: x["answer_count"], reverse=True)
    
    return {
        "form_id": form_id,
        "form_title": form.get("title", form_id),
        "statistics": {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": round(completion_rate, 2),
            "total_answers": total_answers,
            "avg_answers_per_session": round(total_answers / total_sessions, 2) if total_sessions > 0 else 0
        },
        "field_popularity": field_popularity[:10],  # Top 10
        "last_updated": int(time.time())
    }


async def aggregate_all_forms_statistics(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Aggregate statistics for all forms"""
    total_forms = await db.forms.count_documents({})
    total_sessions = await db.sessions.count_documents({})
    
    # Get all forms
    forms = []
    async for form in db.forms.find({}, {"_id": 0}):
        forms.append(form)
    
    # Aggregate per form
    form_stats = []
    for form in forms:
        form_id = form.get("id")
        stats = await aggregate_form_statistics(db, form_id)
        if stats:
            form_stats.append(stats)
    
    # Calculate overall metrics
    total_completed = sum(s["statistics"]["completed_sessions"] for s in form_stats)
    overall_completion_rate = (total_completed / total_sessions * 100) if total_sessions > 0 else 0
    
    # Most popular forms
    form_stats_sorted = sorted(
        form_stats,
        key=lambda x: x["statistics"]["total_sessions"],
        reverse=True
    )
    
    # Most popular fields across all forms
    all_field_counts = {}
    for stats in form_stats:
        for field in stats.get("field_popularity", []):
            field_label = field["label"]
            all_field_counts[field_label] = all_field_counts.get(field_label, 0) + field["answer_count"]
    
    top_fields = sorted(
        [{"label": k, "count": v} for k, v in all_field_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:10]
    
    return {
        "overall": {
            "total_forms": total_forms,
            "total_sessions": total_sessions,
            "total_completed_sessions": total_completed,
            "overall_completion_rate": round(overall_completion_rate, 2),
            "avg_sessions_per_form": round(total_sessions / total_forms, 2) if total_forms > 0 else 0
        },
        "top_forms": form_stats_sorted[:10],
        "top_fields": top_fields,
        "forms": form_stats,
        "last_updated": int(time.time())
    }


async def get_timeseries_data(db: AsyncIOMotorDatabase, days: int = 7) -> Dict[str, Any]:
    """Get time series data for sessions and completions"""
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get all sessions and group by date manually
    # Since sessions might not have createdAt, we'll use _id ObjectId timestamp
    daily_sessions_map = {}
    
    async for session in db.sessions.find({}):
        # Try to get timestamp from _id ObjectId
        session_id = session.get("_id")
        if session_id:
            try:
                # ObjectId contains timestamp
                timestamp = session_id.generation_time.timestamp()
                if start_date.timestamp() <= timestamp <= end_date.timestamp():
                    date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                    daily_sessions_map[date_str] = daily_sessions_map.get(date_str, 0) + 1
            except Exception:
                pass
    
    # Convert to list
    daily_sessions = [
        {"date": date, "sessions": count}
        for date, count in sorted(daily_sessions_map.items())
    ]
    
    return {
        "period": f"{days} days",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily_sessions": daily_sessions
    }


async def upsert_gold_data(db: AsyncIOMotorDatabase, form_id: str = None):
    """Upsert gold layer data for a form or all forms"""
    if form_id:
        stats = await aggregate_form_statistics(db, form_id)
        if stats:
            await db.gold.update_one(
                {"form_id": form_id},
                {"$set": stats},
                upsert=True
            )
    else:
        # Aggregate all
        all_stats = await aggregate_all_forms_statistics(db)
        await db.gold.update_one(
            {"type": "overall"},
            {"$set": all_stats},
            upsert=True
        )


async def create_gold_partitions_by_date(db: AsyncIOMotorDatabase, partition_type: str = "monthly") -> Dict[str, Any]:
    """Create partitioned gold collections based on session dates

    Args:
        db: MongoDB database instance
        partition_type: Type of partitioning ('daily', 'weekly', 'monthly', 'yearly')

    Returns:
        Dict with partition creation results
    """
    created_partitions = []
    errors = []

    try:
        # Get all unique dates from sessions
        date_pipeline = [
            {
                "$match": {
                    "createdAt": {"$exists": True, "$ne": None}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": _get_date_format(partition_type),
                            "date": {"$toDate": {"$multiply": ["$createdAt", 1000]}}
                        }
                    }
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]

        date_groups = await db.sessions.aggregate(date_pipeline).to_list(length=None)

        for date_group in date_groups:
            partition_key = date_group["_id"]
            if not partition_key:
                continue

            try:
                # Create partition collection name
                collection_name = f"gold_sessions_{partition_key.replace('-', '_')}"

                # Get sessions for this date partition
                start_date, end_date = _get_date_range(partition_key, partition_type)
                start_timestamp = int(start_date.timestamp())
                end_timestamp = int(end_date.timestamp())

                # Aggregate data for this partition
                partition_data = await _aggregate_partition_data(
                    db, start_timestamp, end_timestamp, partition_key
                )

                if partition_data:
                    # Insert into partitioned collection
                    await db[collection_name].replace_one(
                        {"partition_key": partition_key},
                        partition_data,
                        upsert=True
                    )

                    created_partitions.append({
                        "collection": collection_name,
                        "partition_key": partition_key,
                        "session_count": partition_data.get("total_sessions", 0),
                        "date_range": {
                            "start": start_date.isoformat(),
                            "end": end_date.isoformat()
                        }
                    })

            except Exception as e:
                errors.append({
                    "partition_key": partition_key,
                    "error": str(e)
                })

        # Create indexes for better performance
        for partition in created_partitions:
            try:
                collection = db[partition["collection"]]
                await collection.create_index("partition_key")
                await collection.create_index("last_updated")
                await collection.create_index([("date_range.start", 1), ("date_range.end", 1)])
            except Exception as e:
                errors.append({
                    "collection": partition["collection"],
                    "error": f"Index creation failed: {str(e)}"
                })

        return {
            "status": "success",
            "partition_type": partition_type,
            "created_partitions": created_partitions,
            "errors": errors,
            "total_partitions": len(created_partitions),
            "total_errors": len(errors)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "partition_type": partition_type
        }


def _get_date_format(partition_type: str) -> str:
    """Get MongoDB date format string for partitioning"""
    formats = {
        "daily": "%Y-%m-%d",
        "weekly": "%Y-W%U",  # Year-Week
        "monthly": "%Y-%m",
        "yearly": "%Y"
    }
    return formats.get(partition_type, "%Y-%m")


def _get_date_range(partition_key: str, partition_type: str) -> tuple[datetime, datetime]:
    """Get start and end dates for a partition key"""
    if partition_type == "daily":
        start_date = datetime.strptime(partition_key, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)
    elif partition_type == "weekly":
        year, week = partition_key.split("-W")
        year, week = int(year), int(week)
        # Get first day of week (Monday)
        start_date = datetime.strptime(f"{year}-{week}-1", "%Y-%U-%w")
        end_date = start_date + timedelta(days=7)
    elif partition_type == "monthly":
        start_date = datetime.strptime(partition_key + "-01", "%Y-%m-%d")
        # Get first day of next month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1)
    elif partition_type == "yearly":
        start_date = datetime.strptime(partition_key + "-01-01", "%Y-%m-%d")
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
    else:
        raise ValueError(f"Unsupported partition type: {partition_type}")

    return start_date, end_date


async def _aggregate_partition_data(db: AsyncIOMotorDatabase, start_timestamp: int, end_timestamp: int, partition_key: str) -> Optional[Dict[str, Any]]:
    """Aggregate gold data for a specific date partition"""
    try:
        # Get all sessions in this date range
        sessions = []
        async for session in db.sessions.find({
            "createdAt": {
                "$gte": start_timestamp,
                "$lt": end_timestamp
            }
        }):
            sessions.append(session)

        if not sessions:
            return None

        # Group sessions by form_id
        form_sessions = {}
        total_sessions = len(sessions)
        total_completed = 0
        total_answers = 0

        for session in sessions:
            form_id = session.get("formId")
            if not form_id:
                continue

            if form_id not in form_sessions:
                form_sessions[form_id] = []

            form_sessions[form_id].append(session)

            # Count answers
            answers = session.get("answers", {})
            total_answers += len(answers)

            # Check if completed (simplified check)
            if answers:
                total_completed += 1

        # Get form details and calculate statistics
        form_stats = []
        for form_id, form_session_list in form_sessions.items():
            try:
                form = await db.forms.find_one({"id": form_id}, {"_id": 0})
                if not form:
                    continue

                session_count = len(form_session_list)
                required_fields = [f["id"] for f in form.get("fields", []) if f.get("required", False)]
                completed_count = 0
                field_answer_counts = {}

                for session in form_session_list:
                    answers = session.get("answers", {})

                    # Count answers per field
                    for field_id, value in answers.items():
                        field_answer_counts[field_id] = field_answer_counts.get(field_id, 0) + 1

                    # Check completion
                    if required_fields:
                        if all(field_id in answers for field_id in required_fields):
                            completed_count += 1
                    elif len(answers) > 0:
                        completed_count += 1

                # Calculate completion rate
                completion_rate = (completed_count / session_count * 100) if session_count > 0 else 0

                # Field popularity
                field_popularity = []
                for field in form.get("fields", []):
                    field_id = field.get("id")
                    answer_count = field_answer_counts.get(field_id, 0)
                    field_popularity.append({
                        "field_id": field_id,
                        "label": field.get("label", field_id),
                        "answer_count": answer_count,
                        "popularity_score": (answer_count / session_count * 100) if session_count > 0 else 0
                    })
                field_popularity.sort(key=lambda x: x["answer_count"], reverse=True)

                form_stats.append({
                    "form_id": form_id,
                    "form_title": form.get("title", form_id),
                    "session_count": session_count,
                    "completed_sessions": completed_count,
                    "completion_rate": round(completion_rate, 2),
                    "total_answers": sum(field_answer_counts.values()),
                    "avg_answers_per_session": round(sum(field_answer_counts.values()) / session_count, 2) if session_count > 0 else 0,
                    "field_popularity": field_popularity[:10]
                })

            except Exception as e:
                continue

        # Overall partition statistics
        partition_data = {
            "partition_key": partition_key,
            "partition_type": "date_based",
            "date_range": {
                "start": datetime.fromtimestamp(start_timestamp).isoformat(),
                "end": datetime.fromtimestamp(end_timestamp).isoformat()
            },
            "total_sessions": total_sessions,
            "total_completed_sessions": total_completed,
            "total_answers": total_answers,
            "completion_rate": round((total_completed / total_sessions * 100), 2) if total_sessions > 0 else 0,
            "forms": form_stats,
            "last_updated": int(time.time())
        }

        return partition_data

    except Exception as e:
        print(f"Error aggregating partition data for {partition_key}: {str(e)}")
        return None


async def get_partitioned_gold_data(db: AsyncIOMotorDatabase, partition_key: str, collection_prefix: str = "gold_sessions_") -> Optional[Dict[str, Any]]:
    """Get gold data from a specific partition

    Args:
        db: MongoDB database instance
        partition_key: Partition key (e.g., '2024-11' for monthly partition)
        collection_prefix: Prefix for partition collection names

    Returns:
        Partition data or None if not found
    """
    try:
        collection_name = f"{collection_prefix}{partition_key.replace('-', '_')}"
        collection = db[collection_name]

        # Check if collection exists
        if collection_name not in await db.list_collection_names():
            return None

        # Get partition data
        partition_data = await collection.find_one({"partition_key": partition_key})
        return partition_data

    except Exception as e:
        print(f"Error getting partitioned data for {partition_key}: {str(e)}")
        return None


async def list_gold_partitions(db: AsyncIOMotorDatabase, collection_prefix: str = "gold_sessions_") -> Dict[str, Any]:
    """List all available gold partitions

    Args:
        db: MongoDB database instance
        collection_prefix: Prefix for partition collection names

    Returns:
        Dict with partition information
    """
    try:
        partitions = []
        collection_names = await db.list_collection_names()

        for collection_name in collection_names:
            if collection_name.startswith(collection_prefix):
                try:
                    collection = db[collection_name]
                    # Get partition metadata
                    partition_doc = await collection.find_one({}, {"partition_key": 1, "date_range": 1, "total_sessions": 1, "last_updated": 1})

                    if partition_doc:
                        partitions.append({
                            "collection_name": collection_name,
                            "partition_key": partition_doc.get("partition_key"),
                            "date_range": partition_doc.get("date_range"),
                            "total_sessions": partition_doc.get("total_sessions", 0),
                            "last_updated": partition_doc.get("last_updated")
                        })

                except Exception as e:
                    print(f"Error reading partition {collection_name}: {str(e)}")
                    continue

        # Sort partitions by partition key
        partitions.sort(key=lambda x: x.get("partition_key", ""), reverse=True)

        return {
            "status": "success",
            "total_partitions": len(partitions),
            "partitions": partitions
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "partitions": []
        }


async def query_gold_partitions_by_date_range(db: AsyncIOMotorDatabase, start_date: str, end_date: str, collection_prefix: str = "gold_sessions_") -> Dict[str, Any]:
    """Query gold partitions within a date range

    Args:
        db: MongoDB database instance
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        collection_prefix: Prefix for partition collection names

    Returns:
        Dict with aggregated data from partitions in date range
    """
    try:
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        partitions = await list_gold_partitions(db, collection_prefix)

        if partitions["status"] != "success":
            return partitions

        relevant_partitions = []
        total_sessions = 0
        total_completed = 0
        total_answers = 0
        all_forms = {}

        for partition in partitions["partitions"]:
            date_range = partition.get("date_range", {})
            if not date_range:
                continue

            partition_start = datetime.fromisoformat(date_range["start"].replace('Z', '+00:00'))
            partition_end = datetime.fromisoformat(date_range["end"].replace('Z', '+00:00'))

            # Check if partition overlaps with query range
            if partition_end > start_dt and partition_start < end_dt:
                relevant_partitions.append(partition)

                # Get detailed data from partition
                partition_data = await get_partitioned_gold_data(db, partition["partition_key"], collection_prefix)
                if partition_data:
                    total_sessions += partition_data.get("total_sessions", 0)
                    total_completed += partition_data.get("total_completed_sessions", 0)
                    total_answers += partition_data.get("total_answers", 0)

                    # Aggregate form data
                    for form in partition_data.get("forms", []):
                        form_id = form["form_id"]
                        if form_id not in all_forms:
                            all_forms[form_id] = {
                                "form_id": form_id,
                                "form_title": form["form_title"],
                                "total_sessions": 0,
                                "completed_sessions": 0,
                                "total_answers": 0,
                                "partitions": []
                            }

                        all_forms[form_id]["total_sessions"] += form["session_count"]
                        all_forms[form_id]["completed_sessions"] += form["completed_sessions"]
                        all_forms[form_id]["total_answers"] += form["total_answers"]
                        all_forms[form_id]["partitions"].append({
                            "partition_key": partition["partition_key"],
                            "session_count": form["session_count"],
                            "completed_sessions": form["completed_sessions"]
                        })

        # Calculate overall completion rate
        completion_rate = (total_completed / total_sessions * 100) if total_sessions > 0 else 0

        # Convert forms dict to list and calculate completion rates
        forms_list = []
        for form_data in all_forms.values():
            form_completion_rate = (form_data["completed_sessions"] / form_data["total_sessions"] * 100) if form_data["total_sessions"] > 0 else 0
            forms_list.append({
                **form_data,
                "completion_rate": round(form_completion_rate, 2),
                "avg_answers_per_session": round(form_data["total_answers"] / form_data["total_sessions"], 2) if form_data["total_sessions"] > 0 else 0
            })

        return {
            "status": "success",
            "query_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "total_partitions": len(relevant_partitions),
            "partitions": relevant_partitions,
            "summary": {
                "total_sessions": total_sessions,
                "total_completed_sessions": total_completed,
                "total_answers": total_answers,
                "overall_completion_rate": round(completion_rate, 2)
            },
            "forms": forms_list
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "query_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }


async def get_device_analytics(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Get device and platform analytics
    
    Returns:
        Dict with device statistics including completion rates per device type
    """
    try:
        device_stats = {
            "mobile": {"sessions": 0, "completed": 0, "total_answers": 0},
            "tablet": {"sessions": 0, "completed": 0, "total_answers": 0},
            "desktop": {"sessions": 0, "completed": 0, "total_answers": 0},
            "unknown": {"sessions": 0, "completed": 0, "total_answers": 0}
        }
        
        # Get all sessions with device info
        async for session in db.sessions.find({}):
            device_type = session.get("client", {}).get("deviceType", "unknown")
            if device_type not in device_stats:
                device_type = "unknown"
            
            device_stats[device_type]["sessions"] += 1
            
            # Check if completed (has answers)
            answers = session.get("answers", {})
            if answers:
                device_stats[device_type]["completed"] += 1
                device_stats[device_type]["total_answers"] += len(answers)
        
        # Calculate completion rates and format response
        device_analytics = []
        total_sessions = 0
        total_completed = 0
        
        for device_type, stats in device_stats.items():
            if stats["sessions"] > 0:
                completion_rate = (stats["completed"] / stats["sessions"] * 100) if stats["sessions"] > 0 else 0
                avg_answers = (stats["total_answers"] / stats["sessions"]) if stats["sessions"] > 0 else 0
                
                device_analytics.append({
                    "device_type": device_type,
                    "sessions": stats["sessions"],
                    "completed_sessions": stats["completed"],
                    "completion_rate": round(completion_rate, 2),
                    "total_answers": stats["total_answers"],
                    "avg_answers_per_session": round(avg_answers, 2)
                })
                
                total_sessions += stats["sessions"]
                total_completed += stats["completed"]
        
        # Sort by session count
        device_analytics.sort(key=lambda x: x["sessions"], reverse=True)
        
        overall_completion_rate = (total_completed / total_sessions * 100) if total_sessions > 0 else 0
        
        return {
            "status": "success",
            "total_sessions": total_sessions,
            "total_completed_sessions": total_completed,
            "overall_completion_rate": round(overall_completion_rate, 2),
            "devices": device_analytics,
            "last_updated": int(time.time())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


async def get_dropoff_analysis(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Get drop-off analysis by field
    
    Analyzes which fields cause users to drop off by comparing
    sessions that started vs sessions that answered each field.
    
    Returns:
        Dict with drop-off rates per field across all forms
    """
    try:
        # Get all forms
        forms = []
        async for form in db.forms.find({}, {"_id": 0}):
            forms.append(form)
        
        # Aggregate field drop-off data
        field_dropoff = {}  # field_id -> {label, sessions_started, sessions_answered, dropoff_rate}
        total_sessions_by_form = {}
        
        for form in forms:
            form_id = form.get("id")
            if not form_id:
                continue
            
            # Count total sessions for this form
            form_sessions_count = await db.sessions.count_documents({"formId": form_id})
            total_sessions_by_form[form_id] = form_sessions_count
            
            # Get all fields in this form
            form_fields = form.get("fields", [])
            
            # Initialize field tracking
            for field in form_fields:
                field_id = field.get("id")
                if not field_id:
                    continue
                
                if field_id not in field_dropoff:
                    field_dropoff[field_id] = {
                        "field_id": field_id,
                        "label": field.get("label", field_id),
                        "sessions_started": 0,
                        "sessions_answered": 0,
                        "forms": []
                    }
                
                field_dropoff[field_id]["sessions_started"] += form_sessions_count
                field_dropoff[field_id]["forms"].append(form_id)
            
            # Count how many sessions answered each field
            async for session in db.sessions.find({"formId": form_id}):
                answers = session.get("answers", {})
                for field_id in answers.keys():
                    if field_id in field_dropoff:
                        field_dropoff[field_id]["sessions_answered"] += 1
        
        # Calculate drop-off rates
        dropoff_analysis = []
        for field_id, data in field_dropoff.items():
            sessions_started = data["sessions_started"]
            sessions_answered = data["sessions_answered"]
            dropoff_count = sessions_started - sessions_answered
            dropoff_rate = (dropoff_count / sessions_started * 100) if sessions_started > 0 else 0
            answer_rate = (sessions_answered / sessions_started * 100) if sessions_started > 0 else 0
            
            dropoff_analysis.append({
                "field_id": field_id,
                "label": data["label"],
                "sessions_started": sessions_started,
                "sessions_answered": sessions_answered,
                "dropoff_count": dropoff_count,
                "dropoff_rate": round(dropoff_rate, 2),
                "answer_rate": round(answer_rate, 2),
                "forms_count": len(data["forms"])
            })
        
        # Sort by drop-off rate (highest first)
        dropoff_analysis.sort(key=lambda x: x["dropoff_rate"], reverse=True)
        
        # Calculate overall impact
        total_sessions = sum(total_sessions_by_form.values())
        
        return {
            "status": "success",
            "total_sessions": total_sessions,
            "total_forms": len(forms),
            "fields_analyzed": len(dropoff_analysis),
            "dropoff_analysis": dropoff_analysis,
            "last_updated": int(time.time())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


async def get_hourly_engagement(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Get hourly engagement patterns
    
    Groups sessions by hour of day and calculates completion rates per hour.
    
    Returns:
        Dict with hourly statistics including sessions and completion rates
    """
    try:
        hourly_stats = {}
        
        # Initialize all 24 hours
        for hour in range(24):
            hourly_stats[hour] = {
                "hour": hour,
                "sessions": 0,
                "completed_sessions": 0,
                "total_answers": 0
            }
        
        # Process all sessions
        async for session in db.sessions.find({}):
            # Get timestamp from createdAt or _id
            timestamp = None
            if session.get("createdAt"):
                timestamp = session.get("createdAt")
            elif session.get("_id"):
                try:
                    timestamp = int(session.get("_id").generation_time.timestamp())
                except Exception:
                    continue
            
            if not timestamp:
                continue
            
            # Get hour of day
            dt = datetime.fromtimestamp(timestamp)
            hour = dt.hour
            
            if hour not in hourly_stats:
                hourly_stats[hour] = {
                    "hour": hour,
                    "sessions": 0,
                    "completed_sessions": 0,
                    "total_answers": 0
                }
            
            hourly_stats[hour]["sessions"] += 1
            
            # Check if completed
            answers = session.get("answers", {})
            if answers:
                hourly_stats[hour]["completed_sessions"] += 1
                hourly_stats[hour]["total_answers"] += len(answers)
        
        # Calculate completion rates and format
        hourly_data = []
        total_sessions = 0
        total_completed = 0
        peak_hour = 0
        best_completion_hour = 0
        max_sessions = 0
        max_completion_rate = 0
        
        for hour in range(24):
            stats = hourly_stats[hour]
            if stats["sessions"] > 0:
                completion_rate = (stats["completed_sessions"] / stats["sessions"] * 100) if stats["sessions"] > 0 else 0
                avg_answers = (stats["total_answers"] / stats["sessions"]) if stats["sessions"] > 0 else 0
                
                hourly_data.append({
                    "hour": hour,
                    "hour_label": f"{hour:02d}:00",
                    "sessions": stats["sessions"],
                    "completed_sessions": stats["completed_sessions"],
                    "completion_rate": round(completion_rate, 2),
                    "total_answers": stats["total_answers"],
                    "avg_answers_per_session": round(avg_answers, 2)
                })
                
                total_sessions += stats["sessions"]
                total_completed += stats["completed_sessions"]
                
                # Track peak hour
                if stats["sessions"] > max_sessions:
                    max_sessions = stats["sessions"]
                    peak_hour = hour
                
                # Track best completion hour
                if completion_rate > max_completion_rate:
                    max_completion_rate = completion_rate
                    best_completion_hour = hour
        
        # Sort by hour
        hourly_data.sort(key=lambda x: x["hour"])
        
        overall_completion_rate = (total_completed / total_sessions * 100) if total_sessions > 0 else 0
        
        return {
            "status": "success",
            "total_sessions": total_sessions,
            "total_completed_sessions": total_completed,
            "overall_completion_rate": round(overall_completion_rate, 2),
            "hourly_data": hourly_data,
            "insights": {
                "peak_hour": peak_hour,
                "peak_hour_label": f"{peak_hour:02d}:00",
                "peak_sessions": max_sessions,
                "best_completion_hour": best_completion_hour,
                "best_completion_hour_label": f"{best_completion_hour:02d}:00",
                "best_completion_rate": round(max_completion_rate, 2)
            },
            "last_updated": int(time.time())
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

