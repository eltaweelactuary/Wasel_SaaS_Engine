# 📘 دليل الدمج الرسمي: محرك "واصل" للترجمة الفورية للغة الإشارة
**Wasel Core AI Engine - B2B API Integration Manual**

مرحباً بفريق التطوير. 
هذا الدليل مخصص لمبرمجي وتطبيقات الواجهة الأمامية (Frontend / App Developers). 
يوضح كيف يمكنكم دمج "محرك واصل للترجمة الفورية" داخل تطبيق المحادثة (Chat App) الخاص بكم بسلاسة.

---

## 🏗️ نظرة عامة على المعمارية
المحرك يعمل كخدمة سحابية (REST API). 
التطبيق الخاص بكم لا يحتاج لتحميل أي نماذج ذكاء اصطناعي (أو YOLO أو MediaPipe). 
كل ما عليكم فعله هو:
1. تشغيل كاميرا جهاز المستخدم.
2. التقاط صورة (Frame) كل ثانية ونصف أو ثانيتين.
3. إرسال الصورة للمحرك عبر `POST` Request.
4. استلام "كلمة الترجمة" وإدراجها فوراً في مربع الكتابة (Chat Text Input).

---

## 🔗 تفاصيل نقطة الاتصال (API Endpoint)

### **POST** `/api/v1/translate`

يُستخدم هذا الرابط لإرسال إطار الصورة واستلام الترجمة.

### 🛡️ المصادقة (Authentication)
نظامنا محمي بمفاتيح وصول. يجب إرسال المفتاح الخاص بشركتكم في الهيدر `X-API-Key`.

**مثال للهيدر (Headers):**
```http
Content-Type: application/json
X-API-Key: YOUR_COMPANY_API_KEY
```

### 📩 شكل الطلب (Request Body)
يجب إرسال الـ Body بصيغة `JSON`.
- **`image_base64`** (String, إجباري): الصورة بصيغة Base64. يمكنك إرسال السلسلة نقية أو مع الـ Data URI (مثل `data:image/jpeg;base64,...`).

**مثال للـ Request:**
```json
{
  "image_base64": "/9j/4AAQSkZJRgABAQEASABIAAD..."
}
```

### 📤 شكل الرد (Response Data)
إذا تمت المعالجة بنجاح (200 OK)، سيرد المحرك بملف JSON يحتوي على الترجمة.

**مثال 1: (يوجد إشارة واضحة)**
```json
{
  "translation": "شكرا",
  "processing_time_ms": 780
}
```

**مثال 2: (لا يوجد إشارة واضحة / صمت)**
```json
{
  "translation": "...",
  "processing_time_ms": 650
}
```

> **ملاحظة برمجية هامة:** كود واجهتكم يجب أن يتجاهل الرسالة إذا كانت الترجمة تساوي `"..."` فهذا يعني أن المستخدم لا يقوم بإشارة حالياً.

---

## 💻 مثال تطبيقي (كيفية ربط الترجمة بالشات)

هذا مثال مبسط بلغة **JavaScript** يوضح الدورة الكاملة (التقاط الصورة ⬅️ الإرسال ⬅️ استقبال الكلمة ولصقها في الشات).

```javascript
// 1. التقاط إطار من الكاميرا (Video Element) ورسمه على (Canvas)
const canvas = document.createElement('canvas');
canvas.width = 512;  // مقاس مقترح لسرعة النقل
canvas.height = 512;
const ctx = canvas.getContext('2d');
ctx.drawImage(videoElement, 0, 0, 512, 512);

// 2. تحويل الصورة إلى Base64
const imageBase64 = canvas.toDataURL('image/jpeg', 0.6); // ضغط 60% لسرعة الـ API

// 3. إرسال الإطار لمحرك واصل
fetch('https://api.wasel-engine.com/api/v1/translate', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'YOUR_COMPANY_API_KEY'
    },
    body: JSON.stringify({ image_base64: imageBase64 })
})
.then(response => response.json())
.then(data => {
    // 4. استلام الرد والتعامل معه
    if (data.translation && data.translation !== "..." && data.translation !== "") {
        
        // جلب مربع إدخال النص الخاص بالشات في تطبيقكم
        const chatInput = document.getElementById("chat-message-input");
        
        // إضافة الكلمة المترجمة بجوار ما كُتب مسبقاً مسافة
        chatInput.value += data.translation + " "; 
        
        // (اختياري): إرسال الرسالة تلقائياً إذا أردتم ذلك
        // sendMessage(); 
    }
})
.catch(error => console.error("API Error:", error));
```

---

## ⚡ نصائح للمطورين (لأفضل أداء وتقليل التأخير Latency)

1. **معدل الإرسال (Polling Rate):** 
   - **لا ترسل 30 إطاراً في الثانية!** هذا سيشكل ضغطاً هائلاً وغير ضروري. الإنسان العادي يقوم بإشارة واحدة أو اثنتين في الثانية كحد أقصى.
   - **المعدل المثالي:** إرسال صورة واحدة كل **1500 إلى 2000 ملي ثانية** (1.5 - 2 ثانية).

2. **حجم الصورة:**
   - الكاميرات الحديثة تلتقط صوراً بدقة 4K أو 1080p، إرسال هذه الأحجام عبر الشبكة يقتل السرعة.
   - **المقاس المثالي:** قم بتصغير الـ (Width / Height) عبر الـ Client-Side قبل التشفير إلى Base64 ليصبح مثلاً `512x512` بكسل أو `640x480`. المحرك قوي ويستطيع فهم الإشارة من الصور الصغيرة.

3. **جودة الضغط (Compression):**
   - احرص على تصدير إطار الفيديو بترميز `JPEG` بجودة مضغوطة تتراوح بين `0.5 ~ 0.7` بدل الإرسال بجودة 100% أو بصيغة `PNG` الثقيلة.
