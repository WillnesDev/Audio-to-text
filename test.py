"""
Audio Transcriber ni test qilish
"""
import requests
import os
import time

def test_server_health():
    """Server holatini tekshirish"""
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Server ishlayapti")
            return True
        else:
            print("❌ Server javob bermayapti")
            return False
    except requests.exceptions.RequestException:
        print("❌ Serverga ulanib bo'lmadi")
        return False

def test_transcription(audio_file_path):
    """Audio transkripsiyasini test qilish"""
    if not os.path.exists(audio_file_path):
        print(f"❌ Audio fayl topilmadi: {audio_file_path}")
        return False
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': f}
            data = {
                'language': 'uz-UZ',
                'model': 'base'
            }
            
            print("🔄 Audio fayl yuborilmoqda...")
            response = requests.post(
                'http://localhost:5000/transcribe',
                files=files,
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    print("✅ Transkripsiya muvaffaqiyatli!")
                    print(f"📝 Matn: {result['text'][:100]}...")
                    print(f"📊 So'zlar: {result['word_count']}")
                    print(f"📊 Belgilar: {result['char_count']}")
                    return True
                else:
                    print(f"❌ Transkripsiya xatoligi: {result['error']}")
                    return False
            else:
                print(f"❌ Server xatoligi: {response.status_code}")
                return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ So'rov xatoligi: {e}")
        return False

def create_test_audio():
    """Test uchun audio fayl yaratish (agar mavjud bo'lmasa)"""
    print("🎵 Test audio fayl yaratilmoqda...")
    
    try:
        from pydub import AudioSegment
        from pydub.generators import Sine
        
        # 5 soniyalik test audio yaratish
        tone = Sine(440).to_audio_segment(duration=5000)  # 440Hz, 5 soniya
        tone.export("test_audio.wav", format="wav")
        
        print("✅ Test audio fayl yaratildi: test_audio.wav")
        return "test_audio.wav"
        
    except ImportError:
        print("❌ pydub kutubxonasi o'rnatilmagan")
        return None
    except Exception as e:
        print(f"❌ Test audio yaratishda xatolik: {e}")
        return None

def main():
    """Asosiy test funksiyasi"""
    print("🧪 Audio Transcriber Test Dasturi")
    print("=" * 40)
    
    # 1. Server holatini tekshirish
    print("\n1️⃣ Server holatini tekshirish...")
    if not test_server_health():
        print("💡 Avval 'python app.py' buyrug'i bilan serverni ishga tushiring")
        return
    
    # 2. Audio fayl topish yoki yaratish
    print("\n2️⃣ Test audio faylini tayyorlash...")
    
    # Mavjud audio fayllarni qidirish
    test_files = ['test_audio.wav', 'test.mp3', 'sample.wav', 'audio.mp3']
    audio_file = None
    
    for file in test_files:
        if os.path.exists(file):
            audio_file = file
            print(f"✅ Audio fayl topildi: {file}")
            break
    
    if not audio_file:
        audio_file = create_test_audio()
    
    if not audio_file:
        print("❌ Test uchun audio fayl topilmadi yoki yaratilmadi")
        print("💡 Qo'lda audio fayl qo'shing va qayta urinib ko'ring")
        return
    
    # 3. Transkripsiyani test qilish
    print("\n3️⃣ Transkripsiyani test qilish...")
    test_transcription(audio_file)
    
    print("\n🏁 Test yakunlandi!")

if __name__ == "__main__":
    main()
