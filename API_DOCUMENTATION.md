# Social Media Agent API Documentation

Complete API reference for the Social Media Agent service.

## Base URL

```
http://YOUR_VM_IP:8000
```

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: `http://YOUR_VM_IP:8000/docs`
- **ReDoc**: `http://YOUR_VM_IP:8000/redoc`

## Authentication

Currently, the API does not require authentication. For production deployment, consider adding API key authentication or OAuth2.

---

## Endpoints

### Health & Status

#### `GET /health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-22T20:00:00",
  "database": "healthy",
  "scheduler": "running"
}
```

#### `GET /`

Get API information.

**Response:**
```json
{
  "message": "Social Media Agent API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### Posts Management

#### `POST /api/posts/create`

Create and publish a new social media post.

**Request Body:**
```json
{
  "with_image": true,
  "dry_run": false,
  "scheduled_for": null
}
```

**Parameters:**
- `with_image` (boolean): Generate an image for the post
- `dry_run` (boolean): Preview post without publishing
- `scheduled_for` (datetime, optional): Schedule post for future publication

**Response:**
```json
{
  "id": 1,
  "content": "Post text content...",
  "image_path": "/path/to/image.png",
  "status": "published",
  "created_at": "2026-01-22T20:00:00",
  "published_at": "2026-01-22T20:00:05",
  "mastodon_url": "https://mastodon.social/@user/123456",
  "error_message": null
}
```

**cURL Example:**
```bash
curl -X POST http://YOUR_VM_IP:8000/api/posts/create \
  -H "Content-Type: application/json" \
  -d '{"with_image": true, "dry_run": false}'
```

---

#### `POST /api/posts/create-with-hitl`

Create a post with Human-in-the-Loop approval via Telegram.

**Request Body:**
```json
{
  "with_image": true
}
```

**Process:**
1. Generates post text and optionally an image
2. Sends to Telegram for approval
3. Allows iterative feedback and regeneration
4. Publishes only after approval

**Response:** Same as `/api/posts/create`

---

#### `GET /api/posts`

List all posts with optional filtering.

**Query Parameters:**
- `status` (string, optional): Filter by status (draft, pending, published, rejected, failed)
- `limit` (integer, default: 100): Maximum number of results
- `offset` (integer, default: 0): Pagination offset

**Response:**
```json
{
  "posts": [
    {
      "id": 1,
      "content": "Post text...",
      "status": "published",
      ...
    }
  ],
  "total": 10,
  "limit": 100,
  "offset": 0
}
```

**cURL Example:**
```bash
curl "http://YOUR_VM_IP:8000/api/posts?status=published&limit=10"
```

---

#### `GET /api/posts/{post_id}`

Get a specific post by ID.

**Response:** Single post object (same format as create response)

---

#### `DELETE /api/posts/{post_id}`

Delete a post.

**Response:**
```json
{
  "message": "Post deleted successfully"
}
```

---

#### `POST /api/posts/{post_id}/approve`

Approve and publish a pending post.

**Response:** Updated post object with `status: "published"`

---

#### `POST /api/posts/{post_id}/reject`

Reject a pending post.

**Response:** Updated post object with `status: "rejected"`

---

### Schedules Management

#### `POST /api/schedules`

Create a new automated posting schedule.

**Request Body:**
```json
{
  "name": "Daily Morning Post",
  "cron_expression": "0 9 * * *",
  "with_image": true,
  "enabled": true
}
```

**Cron Expression Examples:**
- `0 9 * * *` - Every day at 9:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 9 * * 1` - Every Monday at 9:00 AM
- `0 9,17 * * *` - Every day at 9:00 AM and 5:00 PM

**Response:**
```json
{
  "id": 1,
  "name": "Daily Morning Post",
  "cron_expression": "0 9 * * *",
  "with_image": true,
  "enabled": true,
  "last_run": null,
  "next_run": "2026-01-23T09:00:00",
  "created_at": "2026-01-22T20:00:00",
  "updated_at": "2026-01-22T20:00:00"
}
```

**cURL Example:**
```bash
curl -X POST http://YOUR_VM_IP:8000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Post",
    "cron_expression": "0 9 * * *",
    "with_image": true,
    "enabled": true
  }'
```

---

#### `GET /api/schedules`

List all schedules.

**Query Parameters:**
- `enabled_only` (boolean, default: false): Show only enabled schedules

**Response:** Array of schedule objects

---

#### `GET /api/schedules/{schedule_id}`

Get a specific schedule by ID.

---

#### `PUT /api/schedules/{schedule_id}`

Update a schedule.

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "cron_expression": "0 10 * * *",
  "with_image": false,
  "enabled": true
}
```

---

#### `DELETE /api/schedules/{schedule_id}`

Delete a schedule.

---

#### `POST /api/schedules/{schedule_id}/enable`

Enable a schedule.

---

#### `POST /api/schedules/{schedule_id}/disable`

Disable a schedule.

---

### Configuration Management

#### `GET /api/config`

List all configuration key-value pairs.

**Response:**
```json
[
  {
    "key": "setting_name",
    "value": "setting_value",
    "updated_at": "2026-01-22T20:00:00"
  }
]
```

---

#### `GET /api/config/{key}`

Get a specific configuration value.

---

#### `PUT /api/config/{key}`

Update or create a configuration value.

**Request Body:**
```json
{
  "value": "new_value"
}
```

---

#### `DELETE /api/config/{key}`

Delete a configuration value.

---

### Notion Integration

#### `GET /api/config/notion/fetch`

Manually fetch content from Notion and update cache.

**Response:**
```json
{
  "id": 1,
  "content": "Cached Notion content...",
  "fetched_at": "2026-01-22T20:00:00"
}
```

---

#### `GET /api/config/notion/cache`

Get the latest cached Notion content.

---

### Reply Generation

#### `POST /api/config/reply-to-posts`

Trigger reply generation to Mastodon posts.

**Query Parameters:**
- `keyword` (string, optional): Keyword to search for in Mastodon posts
- `num_posts` (integer, default: 5): Number of posts to reply to

**Response:**
```json
{
  "message": "Replies generated successfully",
  "count": 5,
  "results": [...]
}
```

---

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "detail": "Error message description",
  "timestamp": "2026-01-22T20:00:00"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `404` - Not Found
- `500` - Internal Server Error

---

## Workflow Examples

### Example 1: Create and Schedule Daily Posts

```bash
# Create a schedule for daily posts at 9 AM
curl -X POST http://YOUR_VM_IP:8000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Morning Post",
    "cron_expression": "0 9 * * *",
    "with_image": true,
    "enabled": true
  }'

# List all schedules to verify
curl http://YOUR_VM_IP:8000/api/schedules
```

### Example 2: Manual Post with HITL Approval

```bash
# Create post with Telegram approval
curl -X POST http://YOUR_VM_IP:8000/api/posts/create-with-hitl \
  -H "Content-Type: application/json" \
  -d '{"with_image": true}'

# Check Telegram for approval prompt
# Approve/reject/regenerate via Telegram
```

### Example 3: View Post History

```bash
# Get all published posts
curl "http://YOUR_VM_IP:8000/api/posts?status=published"

# Get specific post details
curl http://YOUR_VM_IP:8000/api/posts/1
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider adding rate limiting middleware.

## Monitoring

Monitor the service using:

```bash
# Check health endpoint
curl http://YOUR_VM_IP:8000/health

# View service logs
sudo journalctl -u social-media-agent -f

# Check scheduler status
curl http://YOUR_VM_IP:8000/health | jq '.scheduler'
```
