# AI Campaign Assistant API Reference

All endpoints are mounted under `/api/v1/ai`.

Authentication:
- Header: `X-API-Key: <AI_SERVICE_API_KEY>`
- Constant-time verification (`secrets.compare_digest`).

---

## 1. Generate Campaign Drafts

`POST /api/v1/ai/campaigns/generate`

Generates drafts via configured free-tier LLM and stores them as `pending_approval`.

### Request

```http
POST /api/v1/ai/campaigns/generate HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-API-Key: your_service_api_key

{
  "channel": "sms",
  "language": "hi",
  "tone": "professional",
  "key_facts": {
    "event": "Community Health Fair",
    "date": "2026-12-15",
    "venue": "Gandhi Maidan, Patna",
    "cost": "Free",
    "contact": "1800-XXX-YYYY"
  }
}
```

### Response (202 Accepted)

```json
{
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "pending_approval",
  "drafts": [
    {
      "language": "hi",
      "channel": "sms",
      "text": "सामुदायिक स्वास्थ्य मेला, 2026-12-15 को गांधी मैदान, पटना में आयोजित किया जा रहा है। प्रवेश निःशुल्क। संपर्क: 1800-XXX-YYYY",
      "char_count": 128,
      "within_limit": true,
      "provider": "groq",
      "model": "qwen-qwq-32b"
    }
  ],
  "validation_warnings": [],
  "message": "Drafts generated and saved. Awaiting human approval before any use."
}
```

---

## 2. Get Generation Request & Draft

`GET /api/v1/ai/campaigns/{request_id}`

### Request

```http
GET /api/v1/ai/campaigns/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d HTTP/1.1
Host: localhost:8000
X-API-Key: your_service_api_key
```

### Response (200 OK)

```json
{
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "pending_approval",
  "channel": "sms",
  "language": "hi",
  "tone": "professional",
  "key_facts": {
    "event": "Community Health Fair",
    "date": "2026-12-15",
    "venue": "Gandhi Maidan, Patna",
    "cost": "Free",
    "contact": "1800-XXX-YYYY"
  },
  "created_at": "2026-11-18T20:45:00Z",
  "draft": {
    "text": "सामुदायिक स्वास्थ्य मेला...",
    "char_count": 128,
    "within_limit": true,
    "provider": "groq",
    "model": "qwen-qwq-32b",
    "validation_warnings": []
  }
}
```

---

## 3. Approve or Reject Draft

`POST /api/v1/ai/campaigns/{request_id}/approve`

### Request

```http
POST /api/v1/ai/campaigns/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d/approve HTTP/1.1
Host: localhost:8000
Content-Type: application/json
X-API-Key: your_service_api_key

{
  "action": "approve",
  "reviewer_note": "Verified fact correctness. Approved."
}
```

### Response (200 OK)

```json
{
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "action": "approve",
  "status": "approved",
  "reviewer_note": "Verified fact correctness. Approved."
}
```
