# PTM Engine (Plugin)

This repository contains the core, headless backend API engine for the Parent-Teacher Meeting (PTM) platform. It is designed to be easily plugged into existing ERP systems as a highly scalable microservice SaaS.

## Architecture & Integration

*   **Framework:** Django & Django Ninja
*   **Multi-tenancy:** All models use a `tenant_id` to strictly separate data per school/ERP client.
*   **Authentication:** API Key for Server-to-Server communication, and Client-Signed JWTs for Frontend requests.
*   **Data Sync:** Dispatches Webhooks securely (signed with HMAC SHA256) to the parent ERP whenever a booking status is updated.

---

## Getting Started (For Engine Hosts)

### Prerequisites
*   Python 3.9+
*   Redis (for Celery background tasks)

### Setup Instructions
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations and start the server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
4. In a separate terminal, start Celery to process webhooks and notifications:
   ```bash
   celery -A ptm_core worker -l INFO
   ```

---

## Integration Guide (For Clients / ERPs)

If you have purchased access to the PTM Engine, you will be provided with an `API_KEY` (e.g., `ptm_live_sk_xxxxxx`). Keep this key secret. Do not expose it in your frontend code.

### 1. Server-to-Server Authentication

Whenever your ERP backend needs to communicate with the PTM Engine (e.g., to create events, generate slots, or register webhook URLs), you must include your API Key in the `Authorization` header as a Bearer token.

**Example Request:**
```bash
curl -X POST https://api.your-ptm-engine.com/api/events \
     -H "Authorization: Bearer ptm_live_sk_xxxxxx" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Fall 2026 PTM",
           "date": "2026-10-15",
           "start_time": "09:00",
           "end_time": "15:00",
           "mode": "VIRTUAL"
         }'
```

### 2. Registering your Webhook URL

You must tell the PTM engine where to send data (e.g., when a teacher completes a meeting or adds a remark). 

**Example Request:**
```bash
curl -X PATCH https://api.your-ptm-engine.com/api/webhooks \
     -H "Authorization: Bearer ptm_live_sk_xxxxxx" \
     -H "Content-Type: application/json" \
     -d '{"webhook_url": "https://your-erp.com/api/ptm-webhooks"}'
```

### 3. Frontend / Client-Side Authentication

When a Parent or Teacher accesses the PTM UI in your frontend app, you **should not** pass your secret API Key to their browser. Instead, your ERP Backend must generate a **JWT (JSON Web Token)** and sign it using your `API_KEY`.

**How to generate the token in your ERP (Python Example):**
```python
import jwt
import datetime

# Your ERP generates this token and passes it to your frontend
payload = {
    "tenant_id": "your_tenant_string",
    "user_id": "student_12345", 
    "role": "PARENT",  # Or "TEACHER"
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
}

# Sign it securely with your PTM Engine API KEY!
client_session_token = jwt.encode(payload, "ptm_live_sk_xxxxxx", algorithm="HS256")
```

Your frontend will then use this generated `client_session_token` in the `Authorization: Bearer <TOKEN>` header when making requests to the PTM Engine (like booking a slot). The PTM Engine will verify the signature using your API Key on record.

### 4. Verifying Webhooks

When the PTM Engine sends a webhook to your registered URL, it includes an `X-PTM-Signature` header. This is an HMAC SHA256 signature of the request body, signed using your API Key. You should verify this signature in your ERP to ensure the webhook legitimately came from the PTM Engine.
