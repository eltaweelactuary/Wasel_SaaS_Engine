# 🚀 WASEL CORE AI ENGINE — SAAS EDITION

This is the commercial, White-label B2B API engine for Wasel v4. 
It operates as a **Headless SaaS API** designed to be hosted on your infrastructure (e.g. AWS, Google Cloud Run, DigitalOcean) and consumed by external businesses.

## 🔒 Security Architecture (Proprietary IP Protection)

Unlike providing the source code or a compiled binary to the client, this SaaS architecture ensures **100% protection of your intellectual property**:
1. **Source Code & Prompts:** Kept secret on your server. Clients never see your Egyptian Sign Language prompts or logic.
2. **Google API Keys:** Protected. You pay Google directly and proxy the traffic. Your Google keys are never exposed.
3. **Client Control (API Keys):** You issue `X-API-Key` credentials to your B2B clients. If a client stops paying or breaches contract, you simply remove their key and they lose access instantly.

---

## 💻 Deployment Instructions

### 1. Requirements
Install the necessary python packages:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Before running the API, you must set two environment variables to secure the engine:

**Linux / macOS:**
```bash
export GEMINI_API_KEY="AIzaSyYourPrivateGoogleKey..."
export VALID_CLIENT_KEYS="companyA_key_991,companyB_key_882,demo_key"
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="AIzaSyYourPrivateGoogleKey..."
$env:VALID_CLIENT_KEYS="companyA_key_991,companyB_key_882,demo_key"
```

### 3. Run the Server
```bash
python app.py --port 8000
```
*For production, we recommend wrapping this in `gunicorn` or a similar production WSGI server.*

---

## 🤝 Client Integration Guide

When you sell this service to a B2B partner, provide them with **their specific API key** (from `VALID_CLIENT_KEYS`) and the following instructions:

### Endpoint: Translate Frame
`POST /api/v1/translate`

**Headers Required:**
```http
Content-Type: application/json
X-API-Key: <YOUR_PROVIDED_CLIENT_KEY>
```

**Request Body (JSON):**
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQEASABIAAD..."
}
```

**Success Response (200 OK):**
```json
{
  "processing_time_ms": 780,
  "translation": "شكرا"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing `X-API-Key`.
- `400 Bad Request`: Missing `image_base64` or invalid JSON.
- `500 Server Error`: Issue reaching the Google AI backend.

### Optimization Tips for Clients
Advise your clients to:
1. Resize images to `512x512` before Base64 encoding to reduce network latency.
2. Compress JPEG strings to quality `60%-70%`.
3. Poll the API every `1.5` to `2.0` seconds for real-time video, avoiding 30fps spam.
