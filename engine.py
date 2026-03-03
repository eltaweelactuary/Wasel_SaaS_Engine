import eventlet
eventlet.monkey_patch()

import os, time, base64, io, logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
from PIL import Image
import google.genai as genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("wasel-saas")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VALID_CLIENT_KEYS = [k.strip() for k in os.environ.get("VALID_CLIENT_KEYS", "").split(",") if k.strip()]

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet", ping_timeout=60, ping_interval=25)

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL = "gemini-2.0-flash"

SECRET_SYSTEM_PROMPT = """
أنت خبير ومترجم للغة الإشارة المصرية (Egyptian Sign Language - ESL).
انظر إلى هذا التسلسل الحركي للصور (Motion Sequence) لليد والجسم. هل يقوم الشخص بعمل إشارة معينة بلغة الإشارة؟
إذا نعم: أجب فقط بمعنى الإشارة باللغة 'العربية' في كلمة واحدة أو كلمتين كحد أقصى (مثال: شكرا، نعم، لا، مساعدة، سلام).
إذا لم تكن هناك إشارة واضحة: أجب بالضبط بـ: ...
لا تكتب أي شرح، فقط الكلمة.
"""

def analyze_frames(pil_images_list):
    if not client:
        return "Internal Error", 500

    try:
        contents_payload = [SECRET_SYSTEM_PROMPT] + pil_images_list
        
        response = client.models.generate_content(
            model=MODEL,
            contents=contents_payload,
            config=types.GenerateContentConfig(
                max_output_tokens=20,
                temperature=0.1
            )
        )
        return response.text.strip(), 200
    except Exception as e:
        logger.error(f"API Error: {e}")
        return "Processing Error", 500

MAX_PAYLOAD_SIZE = 500_000  # ~500KB per image max

def decode_images(b64_list):
    """Decode base64 images to PIL, shared by REST and WebSocket."""
    pil_images = []
    for b64_string in b64_list:
        try:
            if len(b64_string) > MAX_PAYLOAD_SIZE:
                logger.warning("Payload too large, skipping frame")
                continue
            if "," in b64_string:
                b64_string = b64_string.split(",")[1]
            img_bytes = base64.b64decode(b64_string)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            pil_img.thumbnail((512, 512))
            pil_images.append(pil_img)
        except Exception as e:
            logger.warning(f"Skipping corrupt frame: {e}")
            continue
    return pil_images

def require_api_key(func):
    def wrapper(*args, **kwargs):
        client_key = request.headers.get("X-API-Key")
        if not client_key or client_key not in VALID_CLIENT_KEYS:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# ═══════════════════════════════════════════════════════
# REST API (backward compatible)
# ═══════════════════════════════════════════════════════

@app.route("/api/v1/translate", methods=["POST"])
@require_api_key
def translate_api():
    start_time = time.time()
    
    if not request.is_json:
        return jsonify({"error": "Bad Request"}), 400
        
    data = request.json
    
    b64_list = []
    if "images_base64" in data and isinstance(data["images_base64"], list):
        b64_list = data["images_base64"]
    elif "image_base64" in data:
        b64_list = [data["image_base64"]]
    else:
        return jsonify({"error": "Missing 'images_base64' array"}), 400

    if len(b64_list) > 5:
        b64_list = b64_list[-5:]

    try:
        pil_images = decode_images(b64_list)
        if not pil_images:
            return jsonify({"error": "Empty images list"}), 400

        result, status_code = analyze_frames(pil_images)
        if status_code != 200:
             return jsonify({"error": "Failed"}), status_code

        ms = int((time.time() - start_time) * 1000)
        
        if result == "...":
            return "", 204
            
        return jsonify({
            "translation": result,
            "processing_time_ms": ms,
            "frames_analyzed": len(pil_images)
        }), 200
        
    except Exception as e:
        logger.error(f"Request Error: {e}")
        return jsonify({"error": "Invalid format"}), 400

# ═══════════════════════════════════════════════════════
# WebSocket API (new – persistent connection, zero overhead)
# ═══════════════════════════════════════════════════════

@socketio.on("connect")
def ws_connect():
    logger.info("WebSocket client connected")

@socketio.on("auth")
def ws_auth(data):
    """Authenticate the WebSocket client with an API key."""
    api_key = data.get("api_key", "") if isinstance(data, dict) else ""
    if api_key not in VALID_CLIENT_KEYS:
        emit("auth_result", {"ok": False, "error": "Unauthorized"})
        disconnect()
        return
    emit("auth_result", {"ok": True})
    logger.info("WebSocket client authenticated")

@socketio.on("frame")
def ws_frame(data):
    """Receive frame(s) from client, process, and emit result instantly."""
    start_time = time.time()
    try:
        b64_list = data.get("images", []) if isinstance(data, dict) else []
        if not b64_list:
            # Single image shorthand
            img = data.get("image", "") if isinstance(data, dict) else ""
            if img:
                b64_list = [img]

        if not b64_list:
            emit("result", {"translation": "..."})
            return

        if len(b64_list) > 5:
            b64_list = b64_list[-5:]

        pil_images = decode_images(b64_list)
        if not pil_images:
            emit("result", {"translation": "..."})
            return

        result, status_code = analyze_frames(pil_images)
        ms = int((time.time() - start_time) * 1000)

        if status_code != 200 or result == "...":
            emit("result", {"translation": "..."})
        else:
            emit("result", {
                "translation": result,
                "processing_time_ms": ms,
                "frames_analyzed": len(pil_images)
            })
    except Exception as e:
        logger.error(f"WS frame error: {e}")
        emit("result", {"translation": "..."})

@socketio.on("disconnect")
def ws_disconnect():
    logger.info("WebSocket client disconnected")

# ═══════════════════════════════════════════════════════

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "ws": True}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
