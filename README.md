# FormBot OCR Stack (Docker Compose + OpenAI Q&A)

## Quickstart (Local Development with LocalStack)

1. Copy env:
   - See `ENV_EXAMPLE.md` and create `.env` in repo root.
   - For LocalStack dev, set `S3_ENDPOINT_URL=http://localstack:4566` and a `FORMS_QUEUE_URL` pointing to LocalStack.

2. Start stack using the development override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

3. Verify services:
- API: http://localhost:8000/healthz
- Frontend: http://localhost:3000

4. Seed sample form:
- The `crawler` uploads a sample PDF to S3.
- LocalStack notification sends SQS message.
- `worker` consumes, OCRs minimally, and writes a form record to Mongo.

5. Use the app:
- Open frontend, select a form, answer questions, generate PDF.

## Production Deployment (e.g. EC2)
- Ensure `.env` exists on the server with production values (API base URL should point to the public host, e.g. `NEXT_PUBLIC_API_BASE_URL=http://YOUR_HOST:8000`).
- On the server, run:

```bash
docker compose up -d --build
```

- Frontend will be exposed on port 80, API on port 8000.
- For HTTPS or custom domains, place a reverse proxy (e.g. Nginx, Traefik) in front.

## Gold Data Partitioning

The system supports time-based partitioning of gold layer data for improved performance and scalability. Gold data contains aggregated statistics from form sessions.

### Creating Partitions

Create partitioned collections based on session dates:

```bash
# Create monthly partitions (default)
curl -X POST "http://localhost:8000/gold/partitions/create"

# Create daily partitions
curl -X POST "http://localhost:8000/gold/partitions/create?partition_type=daily"

# Create weekly partitions
curl -X POST "http://localhost:8000/gold/partitions/create?partition_type=weekly"

# Create yearly partitions
curl -X POST "http://localhost:8000/gold/partitions/create?partition_type=yearly"
```

### Querying Partitioned Data

#### List all partitions:
```bash
curl "http://localhost:8000/gold/partitions"
```

#### Get data from specific partition:
```bash
curl "http://localhost:8000/gold/partitions/2024-11"
```

#### Query partitions by date range:
```bash
curl "http://localhost:8000/gold/partitions/query?start_date=2024-11-01&end_date=2024-11-30"
```

### Partition Types

- **daily**: Collections named `gold_sessions_2024_11_15`
- **weekly**: Collections named `gold_sessions_2024_W46`
- **monthly**: Collections named `gold_sessions_2024_11` (recommended)
- **yearly**: Collections named `gold_sessions_2024`

### Testing Partitioning

Run the test script to verify partitioning functionality:

```bash
cd api
python test_partitioning.py
```

### Benefits of Partitioning

1. **Performance**: Faster queries on specific time ranges
2. **Scalability**: Distribute data across multiple collections
3. **Maintenance**: Easier to archive old partitions
4. **Cost Optimization**: Query only relevant partitions

## Terraform (AWS)
- See `infra/terraform/` for S3 bucket, SQS queue, S3->SQS notification, and basic IAM.


