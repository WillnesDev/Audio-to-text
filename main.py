from flask import Flask, request, jsonify, render_template
import os
import tempfile
import speech_recognition as sr
from pydub import AudioSegment
import whisper
import logging
from werkzeug.utils import secure_filename
import time
import shutil
import platform

# Kerakli kutubxonalarni import qilish
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper kutubxonasi o'rnatilmagan. Faqat Google Speech Recognition ishlatiladi.")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    print("⚠️ SpeechRecognition kutubxonasi o'rnatilmagan.")

# Flask app yaratish
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ruxsat etilgan fayl turlari
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'wma'}

# Whisper modelini yuklash (birinchi ishga tushganda)
whisper_model = None

def load_whisper_model(model_name="base"):
    """Whisper modelini yuklash"""
    global whisper_model
    try:
        if whisper_model is None or whisper_model.model_name != model_name:
            logger.info(f"Whisper {model_name} modeli yuklanmoqda...")
            whisper_model = whisper.load_model(model_name)
            whisper_model.model_name = model_name
            logger.info(f"Whisper {model_name} modeli yuklandi!")
        return whisper_model
    except Exception as e:
        logger.error(f"Whisper modelini yuklashda xatolik: {e}")
        return None

def allowed_file(filename):
    """Fayl turi tekshirish"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def check_ffmpeg():
    """FFmpeg mavjudligini tekshirish"""
    return shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None

def convert_audio_to_wav(input_path, output_path):
    """Audio faylni WAV formatiga aylantirish"""
    try:
        # FFmpeg mavjudligini tekshirish
        if not check_ffmpeg():
            logger.warning("FFmpeg topilmadi, PyDub bilan konvertatsiya qilinmoqda...")
            
            # PyDub bilan konvertatsiya (FFmpeg siz)
            try:
                from pydub import AudioSegment
                from pydub.utils import which
                
                # AudioSegment.converter va AudioSegment.ffmpeg ni None qilish
                AudioSegment.converter = None
                AudioSegment.ffmpeg = None
                AudioSegment.ffprobe = None
                
                # Faylni yuklash
                audio = AudioSegment.from_file(input_path)
                
                # Mono formatga aylantirish va sample rate ni 16kHz ga o'rnatish
                audio = audio.set_channels(1).set_frame_rate(16000)
                
                # WAV formatda saqlash
                audio.export(output_path, format="wav")
                
                logger.info("Audio PyDub bilan muvaffaqiyatli konvertatsiya qilindi")
                return True
                
            except Exception as e:
                logger.error(f"PyDub bilan konvertatsiya xatoligi: {e}")
                return False
        
        # FFmpeg bilan konvertatsiya
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        audio.export(output_path, format="wav")
        
        logger.info("Audio FFmpeg bilan muvaffaqiyatli konvertatsiya qilindi")
        return True
        
    except Exception as e:
        logger.error(f"Audio konvertatsiya qilishda xatolik: {e}")
        return False

def transcribe_with_whisper(audio_path, language="auto", model_name="base"):
    """Whisper yordamida audio ni matnga aylantirish"""
    try:
        # Modelni yuklash
        model = load_whisper_model(model_name)
        if model is None:
            return None, "Whisper modelini yuklashda xatolik"
        
        # Tilni sozlash
        if language == "auto":
            language = None
        elif language == "uz-UZ":
            language = "uz"
        elif language == "ru-RU":
            language = "ru"
        elif language == "en-US":
            language = "en"
        
        # Transkripsiya qilish
        logger.info("Audio transkripsiya qilinmoqda...")
        result = model.transcribe(audio_path, language=language)
        
        return result["text"].strip(), None
        
    except Exception as e:
        logger.error(f"Whisper transkripsiya xatoligi: {e}")
        return None, f"Transkripsiya xatoligi: {str(e)}"

def transcribe_with_speech_recognition(audio_path, language="uz-UZ"):
    """SpeechRecognition kutubxonasi yordamida transkripsiya"""
    try:
        r = sr.Recognizer()
        
        with sr.AudioFile(audio_path) as source:
            # Audio ni yuklash
            audio_data = r.record(source)
            
            # Google Speech Recognition API dan foydalanish
            if language == "auto":
                language = "uz-UZ"  # Default
            
            text = r.recognize_google(audio_data, language=language)
            return text, None
            
    except sr.UnknownValueError:
        return None, "Audio da nutq aniqlanmadi"
    except sr.RequestError as e:
        return None, f"Google Speech Recognition xizmati xatoligi: {e}"
    except Exception as e:
        logger.error(f"SpeechRecognition xatoligi: {e}")
        return None, f"Transkripsiya xatoligi: {str(e)}"

@app.route('/')
def index():
    """Asosiy sahifa"""
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Audio faylni matnga aylantirish"""
    try:
        # FFmpeg holatini tekshirish
        ffmpeg_available = check_ffmpeg()
        if not ffmpeg_available:
            logger.warning("FFmpeg topilmadi, cheklangan funksionallik")
        # Faylni tekshirish
        if 'audio_file' not in request.files:
            return jsonify({'success': False, 'error': 'Audio fayl topilmadi'})
        
        file = request.files['audio_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Fayl tanlanmagan'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Noto\'g\'ri fayl turi'})
        
        # Parametrlarni olish
        language = request.form.get('language', 'auto')
        model_name = request.form.get('model', 'base')
        
        # Vaqtinchalik fayllar yaratish
        with tempfile.TemporaryDirectory() as temp_dir:
            # Asl faylni saqlash
            filename = secure_filename(file.filename)
            input_path = os.path.join(temp_dir, filename)
            file.save(input_path)
            
            # WAV formatiga aylantirish
            wav_path = os.path.join(temp_dir, 'converted.wav')
            if not convert_audio_to_wav(input_path, wav_path):
                return jsonify({'success': False, 'error': 'Audio faylni qayta ishlashda xatolik'})
            
            # Transkripsiya qilish
            if WHISPER_AVAILABLE:
                text, error = transcribe_with_whisper(wav_path, language, model_name)
                if text is None and SR_AVAILABLE:
                    logger.info("Whisper ishlamadi, SpeechRecognition ishlatilmoqda...")
                    text, error = transcribe_with_speech_recognition(wav_path, language)
            elif SR_AVAILABLE:
                text, error = transcribe_with_speech_recognition(wav_path, language)
            else:
                return jsonify({'success': False, 'error': 'Hech qanday transkripsiya kutubxonasi mavjud emas'})
            
            if text is None:
                return jsonify({'success': False, 'error': error or 'Transkripsiya amalga oshmadi'})
            
            # Muvaffaqiyatli natija
            logger.info(f"Transkripsiya muvaffaqiyatli: {len(text)} belgi")
            return jsonify({
                'success': True,
                'text': text,
                'word_count': len(text.split()),
                'char_count': len(text)
            })
            
    except Exception as e:
        logger.error(f"Transkripsiya jarayonida xatolik: {e}")
        return jsonify({'success': False, 'error': 'Server xatoligi'})

@app.route('/health')
def health_check():
    """Server holatini tekshirish"""
    return jsonify({'status': 'OK', 'message': 'Server ishlayapti'})

if __name__ == '__main__':
    # Kerakli papkalarni yaratish
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Audio Transcriber Server ishga tushmoqda...")
    print("📱 Brauzerda http://localhost:5000 ga o'ting")
    
    # Serverni ishga tushirish
    app.run(debug=True, host='0.0.0.0', port=5000)
