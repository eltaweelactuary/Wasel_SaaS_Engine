"""
WASEL CORE AI ENGINE — SAAS EDITION
===================================
This is the protected, commercial API engine. It is designed to be hosted
on your own servers (e.g. Google Cloud Run, AWS, DigitalOcean).

Security Features Added:
1. Client API Keys: The client must send an `X-API-Key` header to use the API.
2. Prompt Protection: The AI Prompt is hidden securely on the server.
3. Gemini Protection: Your Gemini API Key is never exposed to the client.

Usage:
1. Install requirements: pip install -r requirements.txt
2. Set Environment Variables:
   - GEMINI_API_KEY="your_google_key"
   - VALID_CLIENT_KEYS="client_key_1,client_key_2"
3. Run server: python app.py --port 8000
"""

import os, time, base64, io, logging, argparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import google.genai as genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wasel-saas")

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--host", default="0.0.0.0")
args = parser.parse_args()

# ═══════════════════════════════════════
# 🔐 SYSTEM CONFIGURATION & SECURITY
# ═══════════════════════════════════════

# Your private Google key (Never share this!)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set. The API will fail on translation requests.")

# The keys you issue to your clients (e.g. Company A gets key1, Company B gets key2)
# You can set this as an exact string in the environment, comma separated: "key1,key2"
# If testing without strict security, we'll allow a default demo key.
VALID_CLIENT_KEYS_STR = os.environ.get("VALID_CLIENT_KEYS", "demo_client_key_123")
VALID_CLIENT_KEYS = [k.strip() for k in VALID_CLIENT_KEYS_STR.split(",") if k.strip()]

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════
# 🧠 AI ENGINE CONFIGURATION
# ═══════════════════════════════════════
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL = "gemini-2.0-flash"

# The Secret Commercial Prompt
# Arabic output targeting Egyptian Sign Language (ESL)
SECRET_SYSTEM_PROMPT = """
أنت خبير ومترجم للغة الإشارة المصرية (Egyptian Sign Language - ESL).
انظر إلى هذه الصورة لليد والجسم. هل يقوم الشخص بعمل إشارة معينة بلغة الإشارة؟
إذا نعم: أجب فقط بمعنى الإشارة باللغة 'العربية' في كلمة واحدة أو كلمتين كحد أقصى (مثال: شكرا، نعم، لا، مساعدة، سلام).
إذا لم تكن هناك إشارة واضحة: أجب بالضبط بـ: ...
لا تكتب أي شرح، فقط الكلمة.
"""

def analyze_frame(pil_image):
    """Sends frame to Google API with the secret prompt."""
    if not client:
        return "Error: Backend AI not configured.", 500

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[SECRET_SYSTEM_PROMPT, pil_image],
            config=types.GenerateContentConfig(
                max_output_tokens=20,
                temperature=0.1
            )
        )
        return response.text.strip(), 200
    except Exception as e:
        logger.error(f"AI Engine Error: {e}")
        return f"Engine Error: {str(e)[:50]}", 500

# ═══════════════════════════════════════
# 🔌 SAAS REST API ENDPOINTS
# ═══════════════════════════════════════

def require_api_key(func):
    """Decorator to enforce client API key validation."""
    def wrapper(*args, **kwargs):
        client_key = request.headers.get("X-API-Key")
        if not client_key or client_key not in VALID_CLIENT_KEYS:
            logger.warning(f"Unauthorized access attempt with key: {client_key}")
            return jsonify({"error": "Unauthorized", "message": "Invalid or missing X-API-Key header"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/api/v1/translate", methods=["POST"])
@require_api_key
def translate_api():
    """
    Primary SaaS Endpoint for B2B Clients.
    Headers:
        Content-Type: application/json
        X-API-Key: <client_issued_key>
    Body:
        {"image_base64": "..."}
    """
    start_time = time.time()
    
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
        
    data = request.json
    if "image_base64" not in data:
        return jsonify({"error": "Missing 'image_base64' field"}), 400

    try:
        # Decode image
        b64_string = data["image_base64"]
        if "," in b64_string:
            b64_string = b64_string.split(",")[1]
            
        img_bytes = base64.b64decode(b64_string)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        # Resize to save Google API bandwidth and costs
        pil_img.thumbnail((512, 512))
        
        # Call AI Core
        result, status_code = analyze_frame(pil_img)
        if status_code != 200:
             return jsonify({"error": result}), status_code

        ms = int((time.time() - start_time) * 1000)
        logger.info(f"Client Processed | Result: '{result}' | {ms}ms")
        
        return jsonify({
            "translation": result,
            "processing_time_ms": ms
        }), 200
        
    except Exception as e:
        logger.error(f"Malformed Request: {e}")
        return jsonify({"error": "Failed to process image format"}), 400


@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """Public health check endpoint (no API key required)."""
    return jsonify({
        "status": "online",
        "service": "Wasel Core Engine (SaaS Edition)"
    }), 200

# ═══════════════════════════════════════
# 🚀 SERVER STARTUP
# ═══════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "="*50)
    print(" 🚀 WASEL CORE AI ENGINE — SAAS EDITION")
    print("="*50)
    print(f" 📡 Port:               {args.port}")
    print(f" 🔑 Allowed Client Keys: {len(VALID_CLIENT_KEYS)} configured")
    print(f" 🔌 Endpoint:           POST /api/v1/translate")
    print("="*50 + "\n")
    
    app.run(host=args.host, port=args.port, debug=False)
