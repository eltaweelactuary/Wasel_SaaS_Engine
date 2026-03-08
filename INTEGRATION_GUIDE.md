# Wasel SaaS Engine — Integration Guide

> **Konecta AI Team** | v1.1 | March 2026 | Contact: ahmed.eltaweel@konecta.com

## Quick Start

| | Value |
|---|---|
| **Base URL** | `https://wasel-saas-engine-112458895076.europe-west1.run.app` |
| **API Key** | `<YOUR_API_KEY>` |
| **Health** | `GET /api/v1/health` → `{"status": "online"}` |

---

## REST API

```
POST /api/v1/translate
Header: X-API-Key: <YOUR_API_KEY>
```

**Request:**
```json
{ "images_base64": ["data:image/webp;base64,..."] }
```

**Response (200):**
```json
{ "translation": "شكراً", "processing_time_ms": 450, "frames_analyzed": 1 }
```

**Status Codes:**

| Code | Meaning | Action |
|---|---|---|
| `200` | Translation found | Use `translation` field |
| `204` | No gesture detected | Skip (empty body) |
| `400` | Bad request | Fix request format |
| `401` | Invalid API key | Check `X-API-Key` header |
| `429` | Rate limited / quota exceeded | **Backoff & retry** (see below) |

### Handling 429 (Rate Limit)

The engine enforces **30 requests/minute** per API key. If exceeded, or if the AI quota is exhausted, you receive:

```json
{ "error": "Too Many Requests", "retry_after_seconds": 10 }
```

**You MUST implement Exponential Backoff:**

```javascript
async function translateWithBackoff(base64Image, attempt = 0) {
    const res = await fetch(API_URL, { method: 'POST', headers: {...}, body: ... });
    
    if (res.status === 429) {
        const wait = Math.min(5000 * Math.pow(2, attempt), 60000); // 5s, 10s, 20s, max 60s
        console.warn(`Rate limited. Retrying in ${wait/1000}s...`);
        await new Promise(r => setTimeout(r, wait));
        return translateWithBackoff(base64Image, attempt + 1);
    }
    return res;
}
```

### Code Examples

**Python:**
```python
import requests

r = requests.post(
    "https://wasel-saas-engine-112458895076.europe-west1.run.app/api/v1/translate",
    json={"images_base64": [base64_image]},
    headers={"X-API-Key": "<YOUR_API_KEY>"}, timeout=5
)
if r.status_code == 200: print(r.json()["translation"])
elif r.status_code == 429: time.sleep(r.json().get("retry_after_seconds", 10))
```

**cURL:**
```bash
curl -X POST "https://wasel-saas-engine-112458895076.europe-west1.run.app/api/v1/translate" \
  -H "X-API-Key: <YOUR_API_KEY>" -H "Content-Type: application/json" \
  -d '{"images_base64": ["data:image/webp;base64,..."]}'
```

---

## WebSocket API (Real-Time)

Connect via [Socket.IO v4](https://socket.io/):

```
Client → connect
Client → emit('auth', {api_key: '<YOUR_API_KEY>'})
Server → emit('auth_result', {ok: true})

Client → emit('frame', {image: 'data:image/webp;base64,...'})   ← repeat
Server → emit('result', {translation: 'شكراً', processing_time_ms: 450})
```

**JavaScript:**
```javascript
import { io } from "socket.io-client";

const socket = io("https://wasel-saas-engine-112458895076.europe-west1.run.app", 
    { transports: ['websocket'] });

socket.on('connect', () => socket.emit('auth', { api_key: '<YOUR_API_KEY>' }));

socket.on('result', (data) => {
    if (data.translation && data.translation !== "...") 
        console.log("Translation:", data.translation);
});

// Send frame:
socket.emit('frame', { image: canvas.toDataURL('image/webp', 0.3) });
```

---

## Best Practices

| Practice | Details |
|---|---|
| **Image format** | WebP at quality 0.3 (~20-30KB per frame) |
| **Resolution** | 320×240 is sufficient (auto-resized server-side) |
| **Max payload** | **100KB per image** — larger payloads are rejected |
| **Motion detection** | Only send frames when hand is moving — saves quota |
| **Multi-frame** | Send 2–5 frames in `images_base64` array for better accuracy |
| **Rate limit** | 30 req/min per API key — implement Exponential Backoff for 429 |
| **Security** | Never expose the API key in client-side code — proxy through your backend |
