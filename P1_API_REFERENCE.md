# P1 Creator Mode - API Reference

## Schedule Management Endpoints

### GET /schedule/{job_id}
Retrieve schedule information for a job.

**Request:**
```http
GET /schedule/abc123-def456-789 HTTP/1.1
```

**Response (200 OK):**
```json
{
  "job_id": "abc123-def456-789",
  "scheduled_at": "2025-06-15T10:00:00Z"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job abc123 not found"
}
```
or
```json
{
  "detail": "No schedule found for job abc123"
}
```

---

### POST /schedule/{job_id}
Schedule a job for future publishing.

**Request:**
```http
POST /schedule/abc123-def456-789 HTTP/1.1
Content-Type: application/json

{
  "scheduled_at": "2025-06-15T10:00:00Z"
}
```

**Validation Rules:**
- `scheduled_at` must be valid ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- Timestamp must be in the future (UTC)
- Job must exist (has `job_summary.json`)

**Response (200 OK):**
```json
{
  "job_id": "abc123-def456-789",
  "scheduled_at": "2025-06-15T10:00:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "scheduled_at must be in the future (UTC)"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job abc123 not found"
}
```

---

### DELETE /schedule/{job_id}
Cancel/remove a scheduled publish.

**Request:**
```http
DELETE /schedule/abc123-def456-789 HTTP/1.1
```

**Response (200 OK):**
```json
{
  "message": "Schedule removed"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job abc123 not found"
}
```

---

## Library Management Endpoints (Enhanced)

### GET /library
List all jobs with pagination and filtering.

**Query Parameters:**
- `page` (int, default=1) - Page number (1-indexed)
- `per_page` (int, default=20) - Items per page
- `state` (string, optional) - Filter by job state (pending/running/success/failed)
- `language` (string, optional) - Filter by script language

**Request:**
```http
GET /library?page=1&per_page=20&state=success HTTP/1.1
```

**Response (200 OK):**
```json
{
  "entries": [
    {
      "job_id": "abc123-def456-789",
      "topic": "Sanatan Dharma principles",
      "state": "success",
      "encoder": "whisper",
      "fast_path": true,
      "language": "english",
      "duration_sec": 45,
      "created_at": "2025-06-10T08:30:00Z",
      "thumbnail_url": "/artifacts/abc123/thumbnail.jpg",
      "final_video_url": "/artifacts/abc123/final_video.mp4",
      "youtube_url": null,
      "status": "Completed successfully"
    }
  ],
  "total": 15,
  "has_more": true
}
```

---

### POST /library/{job_id}/duplicate
Create a copy of an existing job.

**Request:**
```http
POST /library/abc123-def456-789/duplicate HTTP/1.1
```

**Response (200 OK):**
```json
{
  "new_job_id": "xyz789-new123-456",
  "message": "Job duplicated successfully"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job abc123 not found"
}
```

---

### DELETE /library/{job_id}
Soft delete a job (sets `deleted: true` in job_summary.json).

**Request:**
```http
DELETE /library/abc123-def456-789 HTTP/1.1
```

**Response (200 OK):**
```json
{
  "message": "Job soft deleted"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Job abc123 not found"
}
```

---

## Health Check (Enhanced)

### GET /readyz
Health check with schedule storage validation.

**Response (200 OK):**
```json
{
  "status": "ok",
  "checks": {
    "fastapi": true,
    "pipeline_outputs_ok": true,
    "schedule_store_ok": true
  }
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unavailable",
  "checks": {
    "fastapi": true,
    "pipeline_outputs_ok": true,
    "schedule_store_ok": false
  }
}
```

---

## Frontend API Functions

### TypeScript API Client (`platform/frontend/src/lib/api.ts`)

```typescript
// Fetch library with filters
export async function fetchLibrary(
  page: number = 1,
  perPage: number = 20,
  filters?: { state?: string; language?: string }
): Promise<LibraryResponse>

// Schedule job for publishing
export async function schedulePublish(
  jobId: string,
  scheduledAt: string  // ISO 8601 format
): Promise<{ job_id: string; scheduled_at: string }>

// Cancel scheduled publish
export async function unschedule(
  jobId: string
): Promise<{ message: string }>

// Duplicate job
export async function duplicateProject(
  jobId: string
): Promise<{ new_job_id: string; message: string }>

// Soft delete job
export async function deleteProject(
  jobId: string
): Promise<{ message: string }>
```

---

## Data Models

### LibraryEntry (TypeScript)
```typescript
export interface LibraryEntry {
  job_id: string;
  topic?: string;
  state: 'pending' | 'running' | 'success' | 'failed';
  encoder?: string;
  fast_path?: boolean;
  language?: string;
  duration_sec?: number;
  created_at?: string;  // ISO 8601
  thumbnail_url?: string;
  final_video_url?: string;
  youtube_url?: string;
  status?: string;
}
```

### LibraryResponse (TypeScript)
```typescript
export interface LibraryResponse {
  entries: LibraryEntry[];
  total: number;
  has_more: boolean;
}
```

### Schedule (Backend JSON)
**File:** `pipeline_outputs/{job_id}/schedule.json`
```json
{
  "job_id": "abc123-def456-789",
  "scheduled_at": "2025-06-15T10:00:00Z"
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes
- `200 OK` - Success
- `400 Bad Request` - Invalid input (e.g., past timestamp, invalid ISO format)
- `404 Not Found` - Job or schedule doesn't exist
- `500 Internal Server Error` - Server-side error (logged)
- `503 Service Unavailable` - Health check failed

---

## Usage Examples

### Schedule a Job (Frontend)
```typescript
import { schedulePublish } from '../lib/api';

// User picks June 15, 2025 at 10:00 AM UTC
const scheduledTime = '2025-06-15T10:00:00Z';

try {
  const result = await schedulePublish('abc123-def456-789', scheduledTime);
  alert(`Scheduled for ${result.scheduled_at}`);
} catch (err) {
  alert(`Failed to schedule: ${err.message}`);
}
```

### Fetch Completed Jobs Only
```typescript
import { fetchLibrary } from '../lib/api';

const data = await fetchLibrary(1, 20, { state: 'success' });
console.log(`Found ${data.total} completed jobs`);
data.entries.forEach(entry => {
  console.log(`- ${entry.topic} (${entry.job_id})`);
});
```

### Cancel Scheduled Publish
```typescript
import { unschedule } from '../lib/api';

await unschedule('abc123-def456-789');
alert('Schedule cancelled');
```

---

## Testing

### Run All P1 Tests
```powershell
# From project root
pytest tests/test_p1_creator.py -v

# Run specific test
pytest tests/test_p1_creator.py::test_schedule_set_and_get -v

# With coverage
pytest tests/test_p1_creator.py --cov=platform.routes.schedule
```

### Manual API Testing (curl)
```powershell
# Schedule a job
curl -X POST http://localhost:8000/schedule/abc123 `
  -H "Content-Type: application/json" `
  -d '{"scheduled_at": "2025-12-31T23:59:59Z"}'

# Get schedule
curl http://localhost:8000/schedule/abc123

# Cancel schedule
curl -X DELETE http://localhost:8000/schedule/abc123

# List completed jobs
curl "http://localhost:8000/library?state=success"
```

---

**Last Updated:** 2025-01-XX  
**API Version:** P1 (Post-MVP Creator Mode)
