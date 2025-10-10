from gtts import gTTS
import os
from django.conf import settings
import uuid


def text_to_speech(text, lang='en'):

    """
    Преобразование текста в речь через gTTS
    Возвращает URL к аудиофайлу
    """

    try:
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(audio_dir, exist_ok=True)

        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(audio_dir, filename)

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filepath)

        # Возвращаем и путь для бота, и URL для веба
        return {
            'filepath': filepath,  # для бота: /full/path/file.mp3
            'url': f"/media/audio/{filename}"  # для веба: /media/audio/file.mp3
        }

    except Exception as e:
        print(f"TTS Error: {e}")
        return None