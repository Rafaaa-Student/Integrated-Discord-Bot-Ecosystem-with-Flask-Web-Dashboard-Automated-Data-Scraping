import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN warnings
import warnings
warnings.filterwarnings('ignore')
import tensorflow as tf
# Tambahan kalau masih muncul warning deprecated
tf.get_logger().setLevel('ERROR')
import tf_keras
from PIL import Image, ImageOps
import numpy as np
import asyncio
import concurrent.futures
import threading
import re
import requests
from dotenv import load_dotenv

# Load environment variables for AI
load_dotenv()

# Load modelnya sekali saja di sini dengan tf_keras untuk kompatibilitas Teachable Machine
model = tf_keras.models.load_model("keras_model.h5", compile=False)
labels = open("labels.txt", "r").readlines()

# ==================== IMAGE CLASSIFICATION ====================
def check_image(image_path):
    # Logika pengolahan gambar (Resize ke 224x224 sesuai standar TM)
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    image = Image.open(image_path).convert("RGB")
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    
    # turn the image into a numpy array
    image_array = np.asarray(image)
    
    # Normalize the image
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    
    # Load the image into the array
    data[0] = normalized_image_array
    
    # Predicts the model
    prediction = model.predict(data)
    
    # Ambil hasil prediksi tertinggi
    index = np.argmax(prediction)
    class_name = labels[index]
    confidence_score = prediction[0][index]
    
    return class_name.strip(), confidence_score

# ==================== AI GENERATIVE (GEMINI) ====================
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        AI_AVAILABLE = True
    else:
        AI_AVAILABLE = False
        print("WARNING: GEMINI_API_KEY not found in .env file")
except Exception as e:
    AI_AVAILABLE = False
    print(f"WARNING: Failed to initialize Gemini AI: {e}")

def list_gemini_models():
    """List available Gemini models for debugging"""
    try:
        import google.generativeai as genai
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            models = genai.list_models()
            print("Available Gemini Models:")
            for model in models:
                print(f"  - {model.name} (supported methods: {model.supported_generation_methods})")
            return models
        else:
            print("GEMINI_API_KEY not found")
            return None
    except Exception as e:
        print(f"Error listing models: {e}")
        return None

# Dedicated event loop thread for AI calls.
# This avoids "Event loop is closed" and "Future attached to a different loop"
# by ensuring all Gemini async calls stay on one loop/thread.
_ai_event_loop = None
_ai_loop_thread = None
_ai_loop_lock = threading.Lock()

def _run_ai_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def get_ai_event_loop():
    """Get or create a dedicated, long-lived event loop thread."""
    global _ai_event_loop, _ai_loop_thread
    with _ai_loop_lock:
        should_create = (
            _ai_event_loop is None
            or _ai_event_loop.is_closed()
            or _ai_loop_thread is None
            or not _ai_loop_thread.is_alive()
        )
        if should_create:
            _ai_event_loop = asyncio.new_event_loop()
            _ai_loop_thread = threading.Thread(
                target=_run_ai_loop,
                args=(_ai_event_loop,),
                daemon=True
            )
            _ai_loop_thread.start()
        return _ai_event_loop

def _format_ai_text(text):
    """Normalize AI output so it stays readable and structured."""
    if not text:
        return ""

    cleaned = text.replace("\r\n", "\n").strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Normalize common bullet marks to a consistent style
    cleaned = re.sub(r"(?m)^\s*[•●◦▪]\s+", "- ", cleaned)

    # If there are very long lines, split roughly every 20-24 words
    lines = []
    for raw_line in cleaned.split("\n"):
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        words = line.split()
        if len(words) <= 24 or re.match(r"^(\d+\.|-)\s+", line):
            lines.append(line)
            continue

        chunk = []
        for word in words:
            chunk.append(word)
            if len(chunk) >= 22:
                lines.append(" ".join(chunk))
                chunk = []
        if chunk:
            lines.append(" ".join(chunk))

    return "\n".join(lines).strip()

async def tanyakan_zenn(pesan_user, conversation_history=None):
    """
    Fungsi untuk bertanya ke AI Zenn VII
    Args:
        pesan_user: Pesan dari user
        conversation_history: Riwayat percakapan (list of dict dengan 'role' dan 'content')
    Returns:
        response_text: Jawaban dari AI
    """
    if not AI_AVAILABLE:
        return "Maaf, AI Zenn sedang tidak tersedia. Pastikan GEMINI_API_KEY sudah di-set di file .env"
    
    try:
        # Buat prompt dengan kepribadian Zenn VII (simplified for speed)
        system_prompt = """Kamu adalah Zenn VII, asisten lingkungan yang santai dan edukatif.
Jawab dalam bahasa Indonesia, maksimal 2 paragraf pendek. Maksimal 1 emoji."""
        
        # Jika ada riwayat percakapan, tambahkan ke context (limit to 3 for speed)
        if conversation_history:
            context = "Riwayat:\n"
            for msg in conversation_history[-3:]:
                role = "User" if msg['role'] == 'user' else "Zenn"
                context += f"{role}: {msg['content'][:100]}...\n"  # Truncate for speed
            context += "\n"
        else:
            context = ""
        
        full_prompt = f"{system_prompt}\n\n{context}Pertanyaan: {pesan_user}\nJawab:"
        
        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        response = await asyncio.to_thread(tanyakan_zenn_sync, full_prompt)
        return _format_ai_text(response)
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "Maaf, terjadi error saat memproses pesan kamu. Coba lagi nanti ya!"

def tanyakan_zenn_sync(pesan_user, conversation_history=None):
    """Synchronous version of tanyakan_zenn for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "Maaf, GEMINI_API_KEY tidak ditemukan"
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-2.5-flash-lite')
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, pesan_user)
            try:
                response = future.result(timeout=90)  # 90 second timeout
                return response.text
            except concurrent.futures.TimeoutError:
                return "Maaf, AI terlalu lama merespon. Coba lagi nanti ya!"
    except Exception as e:
        print(f"Error in sync AI call: {e}")
        return f"Error: {str(e)}"

async def tebak_unsur_dari_benda(nama_benda):
    """
    Fungsi untuk menebak unsur kimia utama dari nama benda
    Args:
        nama_benda: Nama benda yang dianalisis
    Returns:
        list: List of element symbols (e.g., ['Fe', 'Cr'])
    """
    if not AI_AVAILABLE:
        return []
    
    try:
        prompt = f"""Analisis benda "{nama_benda}" dan tentukan 2-5 unsur kimia utama yang menyusunnya.
        
Rules:
- Hanya berikan SIMBOL UNSUR (contoh: Fe, C, O, H, Na, Cl)
- Format jawaban: Simbol1, Simbol2, Simbol3 (dipisahkan koma)
- Maksimal 5 unsur
- Jangan berikan penjelasan, hanya simbol saja

Contoh:
- Sendok besi: Fe, C
- Garam dapur: Na, Cl
- Air: H, O
- Emas: Au

Jawab untuk "{nama_benda}":"""
        
        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        response = await asyncio.to_thread(tebak_unsur_dari_benda_sync, prompt)
        return response
        
    except Exception as e:
        print(f"Error tebak unsur: {e}")
        return []

def tebak_unsur_dari_benda_sync(nama_benda):
    """Synchronous version of tebak_unsur_dari_benda for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return []
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, nama_benda)
            try:
                response = future.result(timeout=60)  # 60 second timeout
                result = response.text.strip()
                
                # Parse the result to get element symbols
                elements = [e.strip() for e in result.split(',')]
                # Filter only valid element symbols (1-2 letters, first uppercase)
                valid_elements = []
                for elem in elements:
                    if elem and len(elem) <= 2 and elem[0].isupper():
                        valid_elements.append(elem)
                
                return valid_elements[:5]  # Max 5 elements
            except concurrent.futures.TimeoutError:
                print("Timeout saat menebak unsur")
                return []
    except Exception as e:
        print(f"Error in sync tebak unsur call: {e}")
        return []

# ==================== WIKIPEDIA EXPLORATION ====================
def fetch_wiki_data(query):
    """
    Fetch data from Wikipedia API (Indonesian)
    Args:
        query: Search query (topic name)
    Returns:
        dict: Contains title, summary, url, thumbnail or None if error
    """
    # Membersihkan input agar sesuai format URL (spasi jadi underscore)
    formatted_query = query.replace(" ", "_")
    
    # URL REST API Wikipedia (Bahasa Indonesia)
    url = f"https://id.wikipedia.org/api/rest_v1/page/summary/{formatted_query}"
    
    # SANGAT PENTING: Wikipedia mewajibkan User-Agent yang jelas
    headers = {
        'User-Agent': 'ZennVII_Bot/1.0 (https://github.com/Rafaaa-Student; tuanksatria02@gmail.com)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            raw_summary = data.get("extract", "")
            # Membersihkan teks sampah Wikipedia
            clean_summary = raw_summary.replace("code: en is deprecated", "").strip()
            
            return {
                "title": data.get("title"),
                "summary": clean_summary, # Ini teks ringkasannya yang sudah bersih
                "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                "thumbnail": data.get("thumbnail", {}).get("source") # Link gambar jika ada
            }
        else:
            return None
    except Exception as e:
        print(f"Error MediaWiki: {e}")
        return None

async def ringkas_wikipedia_async(teks_wikipedia):
    """
    Ringkas teks Wikipedia dengan Gemini
    Args:
        teks_wikipedia: Teks dari Wikipedia yang akan diringkas
    Returns:
        str: Ringkasan maksimal 20 kata dengan gaya mentor lingkungan
    """
    if not AI_AVAILABLE:
        return "Maaf, AI tidak tersedia."
    
    try:
        prompt = f"""Ringkas teks Wikipedia berikut menjadi maksimal 20 kata dengan gaya mentor lingkungan. Fokus pada fakta utama. JANGAN berikan salam pembuka atau penutup. Teks: {teks_wikipedia}"""
        
        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        response = await asyncio.to_thread(ringkas_wikipedia_sync, prompt)
        return response
    except Exception as e:
        print(f"Error ringkas Wikipedia: {e}")
        return "Maaf, gagal meringkas teks."

def ringkas_wikipedia_sync(teks_wikipedia):
    """Synchronous version of ringkas_wikipedia for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "Maaf, GEMINI_API_KEY tidak ditemukan"
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, teks_wikipedia)
            try:
                response = future.result(timeout=60)  # 60 second timeout
                return response.text.strip()
            except concurrent.futures.TimeoutError:
                return "Maaf, AI terlalu lama merespon. Coba lagi nanti ya!"
    except Exception as e:
        print(f"Error in sync Wikipedia call: {e}")
        return f"Error: {str(e)}"

async def jelaskan_sampah(label, confidence_score):
    """
    Fungsi untuk menjelaskan hasil klasifikasi sampah dengan Gemini AI
    Args:
        label: Label hasil klasifikasi dari Keras AI
        confidence_score: Confidence score dari Keras AI (0-1)
    Returns:
        response_text: Penjelasan edukatif dari AI Zenn VII
    """
    if not AI_AVAILABLE:
        return f"✅ AI Yakin ini {label} sampahnya ({confidence_score*100:.0f}%). +10 Poin! 🌿"
    
    try:
        # Bersihkan label dari whitespace dan karakter khusus
        label_clean = label.strip().replace(" ", "_")
        
        system_prompt = """Kamu adalah Zenn VII, asisten cerdas bertema lingkungan yang keren dan santai.
Tugas: Jelaskan hasil klasifikasi sampah dengan cara yang edukatif dan bervariasi.
Karakteristik:
- Jawab dengan gaya anak muda yang keren
- Berikan informasi edukatif tentang jenis sampah tersebut
- Berikan tips cara mengelola sampah tersebut dengan benar
- Gunakan emoji sesekali untuk bikin fun
- Variasi jawaban setiap kali agar tidak monoton
- Pastikan jawaban pendek tapi informatif (maksimal 3 kalimat)"""
        
        full_prompt = f"""{system_prompt}

Hasil klasifikasi AI: {label_clean} dengan tingkat keyakinan {confidence_score*100:.0f}%.

Jelaskan jenis sampah ini dan berikan tips cara mengelolanya dengan benar. Jawab dengan gaya santai dan edukatif!"""
        
        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        response = await asyncio.to_thread(jelaskan_sampah_sync, full_prompt)
        return response
        
    except Exception as e:
        print(f"Error generating AI explanation: {e}")
        return f"✅ AI Yakin ini {label} sampahnya ({confidence_score*100:.0f}%). +10 Poin! 🌿"

def jelaskan_sampah_sync(full_prompt):
    """Synchronous version of jelaskan_sampah for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "Maaf, GEMINI_API_KEY tidak ditemukan"
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, full_prompt)
            try:
                response = future.result(timeout=60)  # 60 second timeout
                return response.text
            except concurrent.futures.TimeoutError:
                return "Maaf, AI terlalu lama merespon. Coba lagi nanti ya!"
    except Exception as e:
        print(f"Error in sync jelaskan sampah call: {e}")
        return f"Error: {str(e)}"

async def validate_image_with_gemini(image_path, target_object):
    """
    Fungsi untuk validasi gambar dengan Gemini AI untuk exclusive event
    Args:
        image_path: Path ke gambar yang akan divalidasi
        target_object: Objek yang dicari dalam gambar
    Returns:
        "VALID" jika gambar mengandung target_object, "INVALID" jika tidak
    """
    if not AI_AVAILABLE:
        return "INVALID"
    
    try:
        # Load image
        import google.generativeai as genai
        from PIL import Image
        
        image = Image.open(image_path)
        
        # System prompt untuk validasi sederhana
        system_prompt = f"""Kamu adalah validator gambar. Tugasmu hanya satu: periksa apakah dalam gambar ini ada {target_object}. 
Jawab HANYA dengan satu kata: "VALID" jika ada, atau "INVALID" jika tidak ada. 
Jangan berikan teks lain, penjelasan, atau format apapun selain "VALID" atau "INVALID"."""
        
        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        result = await asyncio.to_thread(validate_image_with_gemini_sync, image_path, system_prompt)
        return result
        
    except Exception as e:
        print(f"Error validating image with Gemini: {e}")
        return "INVALID"

def validate_image_with_gemini_sync(image_path, system_prompt):
    """Synchronous version of validate_image_with_gemini for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        from PIL import Image
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "INVALID"
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
        image = Image.open(image_path)
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, [system_prompt, image])
            try:
                response = future.result(timeout=60)  # 60 second timeout
                result = response.text.strip().upper()
                
                # Ensure only VALID or INVALID is returned
                if "VALID" in result:
                    return "VALID"
                else:
                    return "INVALID"
            except concurrent.futures.TimeoutError:
                print("Timeout saat validasi gambar")
                return "INVALID"
    except Exception as e:
        print(f"Error in sync validate image call: {e}")
        return "INVALID"

async def respons_scan(label, confidence_score, target_object, is_target_match):
    """
    Generate jawaban variatif untuk command scan berbasis hasil Keras.
    Args:
        label: Label klasifikasi dari Keras
        confidence_score: Confidence score (0-1)
        target_object: Objek target yang dicari
        is_target_match: True jika gambar sesuai target dan valid untuk poin
    Returns:
        response_text: Jawaban gaya Zenn VII yang variatif
    """
    confidence_pct = confidence_score * 100
    status_text = "sesuai target" if is_target_match else "belum sesuai target"

    if not AI_AVAILABLE:
        if is_target_match:
            return f"✅ Scan valid: {label} ({confidence_pct:.0f}%). Keren, kamu berhasil memilah target dengan tepat!"
        return f"❌ Scan belum valid: {label} ({confidence_pct:.0f}%). Coba foto lebih dekat dan pencahayaan lebih terang."

    try:
        system_prompt = """Kamu adalah Zenn VII, asisten lingkungan yang suportif dan rapi.
Tugas: respons hasil scan sampah dari model klasifikasi.
Aturan format:
- Jawaban ringkas: 2-4 baris.
- Baris 1: status singkat.
- Baris 2-3: alasan atau saran praktis.
- Jika perlu list, pakai format bullet (-).
- Emoji maksimal 1.
Gaya:
- Positif, memotivasi, dan jelas.
- Sebutkan confidence secara natural."""

        full_prompt = f"""{system_prompt}

Hasil scan model:
- label: {label}
- confidence: {confidence_pct:.0f}%
- status: {status_text}

Buat jawaban sebagai Zenn VII dalam bahasa Indonesia."""

        # Generate response using sync version in thread to avoid event loop conflicts
        import asyncio
        response = await asyncio.to_thread(respons_scan_sync, full_prompt)
        return _format_ai_text(response)
    except Exception as e:
        print(f"Error generating scan response: {e}")
        if is_target_match:
            return f"✅ Scan valid: {label} ({confidence_pct:.0f}%). Mantap, pemilahanmu sudah tepat!"
        return f"❌ Scan belum valid: {label} ({confidence_pct:.0f}%). Coba foto lebih dekat dan lebih fokus ke objek."

def respons_scan_sync(full_prompt):
    """Synchronous version of respons_scan for use with asyncio.to_thread"""
    try:
        import google.generativeai as genai
        import concurrent.futures
        
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            return "Maaf, GEMINI_API_KEY tidak ditemukan"
        
        genai.configure(api_key=GEMINI_API_KEY)
        ai_model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
        # Add timeout to prevent hanging
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(ai_model.generate_content, full_prompt)
            try:
                response = future.result(timeout=60)  # 60 second timeout
                return response.text
            except concurrent.futures.TimeoutError:
                return "Maaf, AI terlalu lama merespon. Coba lagi nanti ya!"
    except Exception as e:
        print(f"Error in sync respons scan call: {e}")
        return f"Error: {str(e)}"
