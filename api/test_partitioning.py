#!/usr/bin/env python3
"""
Test script for gold data partitioning functionality
Run with: python test_partitioning.py
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from gold_aggregator import (
    create_gold_partitions_by_date,
    list_gold_partitions,
    get_partitioned_gold_data,
    query_gold_partitions_by_date_range
)


async def test_partitioning():
    """Test the partitioning functionality"""
    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/forms")
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.get_default_database() if "/" in mongodb_uri.split("mongodb://")[-1] else client["forms"]

    try:
        print("🔄 Testing Gold Data Partitioning")
        print("=" * 50)

        # Step 1: Create monthly partitions
        print("\n1. Creating monthly partitions...")
        result = await create_gold_partitions_by_date(db, "monthly")
        print(f"Status: {result['status']}")
        print(f"Created partitions: {result['total_partitions']}")
        if result['errors']:
            print(f"Errors: {len(result['errors'])}")

        # Step 2: List all partitions
        print("\n2. Listing all partitions...")
        partitions = await list_gold_partitions(db)
        print(f"Total partitions found: {partitions['total_partitions']}")
        for partition in partitions['partitions'][:5]:  # Show first 5
            print(f"  - {partition['collection_name']}: {partition['total_sessions']} sessions")

        # Step 3: Get data from a specific partition (if any exist)
        if partitions['partitions']:
            partition_key = partitions['partitions'][0]['partition_key']
            print(f"\n3. Getting data from partition: {partition_key}")
            partition_data = await get_partitioned_gold_data(db, partition_key)
            if partition_data:
                print(f"Partition has {partition_data['total_sessions']} total sessions")
                print(f"Completion rate: {partition_data['completion_rate']}%")
            else:
                print("No data found in partition")

        # Step 4: Query partitions by date range
        print("\n4. Querying partitions by date range...")
        # Query last 30 days
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        query_result = await query_gold_partitions_by_date_range(
            db,
            start_date.isoformat(),
            end_date.isoformat()
        )
        print(f"Query status: {query_result['status']}")
        if query_result['status'] == 'success':
            print(f"Found {query_result['total_partitions']} partitions in range")
            print(f"Total sessions: {query_result['summary']['total_sessions']}")
            print(f"Overall completion rate: {query_result['summary']['overall_completion_rate']}%")

        print("\n✅ Partitioning test completed successfully!")

    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_partitioning())
