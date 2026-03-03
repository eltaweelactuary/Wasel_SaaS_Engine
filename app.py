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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VALID_CLIENT_KEYS = [k.strip() for k in os.environ.get("VALID_CLIENT_KEYS", "").split(",") if k.strip()]

app = Flask(__name__)
CORS(app)

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
        # Pass the prompt and the sequence of images to Gemini to understand the motion
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

def require_api_key(func):
    def wrapper(*args, **kwargs):
        client_key = request.headers.get("X-API-Key")
        if not client_key or client_key not in VALID_CLIENT_KEYS:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/api/v1/translate", methods=["POST"])
@require_api_key
def translate_api():
    start_time = time.time()
    
    if not request.is_json:
        return jsonify({"error": "Bad Request"}), 400
        
    data = request.json
    
    # Accept either historical single image or new multi-frame array
    b64_list = []
    if "images_base64" in data and isinstance(data["images_base64"], list):
        b64_list = data["images_base64"]
    elif "image_base64" in data:
        b64_list = [data["image_base64"]]
    else:
        return jsonify({"error": "Missing 'images_base64' array"}), 400

    # Limit to maximum 5 frames per request to prevent abuse and latency
    if len(b64_list) > 5:
        b64_list = b64_list[-5:]

    try:
        pil_images = []
        for b64_string in b64_list:
            if "," in b64_string:
                b64_string = b64_string.split(",")[1]
                
            img_bytes = base64.b64decode(b64_string)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            pil_img.thumbnail((512, 512))
            pil_images.append(pil_img)
        
        if not pil_images:
            return jsonify({"error": "Empty images list"}), 400

        result, status_code = analyze_frames(pil_images)
        if status_code != 200:
             return jsonify({"error": "Failed"}), status_code

        ms = int((time.time() - start_time) * 1000)
        
        return jsonify({
            "translation": result,
            "processing_time_ms": ms,
            "frames_analyzed": len(pil_images)
        }), 200
        
    except Exception as e:
        logger.error(f"Request Error: {e}")
        return jsonify({"error": "Invalid format"}), 400

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({"status": "online"}), 200

if __name__ == "__main__":
    app.run(host=args.host, port=args.port, debug=False)
