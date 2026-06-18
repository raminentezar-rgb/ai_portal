from accounts.decorators import check_credits, deduct_credit
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import speech_recognition as sr
from gtts import gTTS
from deep_translator import GoogleTranslator
import PyPDF2
import docx
import os
import tempfile

def extract_text_from_file(uploaded_file):
    filename = uploaded_file.name.lower()
    text = ""
    if filename.endswith('.txt'):
        text = uploaded_file.read().decode('utf-8')
    elif filename.endswith('.pdf'):
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif filename.endswith('.docx'):
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

def text_to_voice(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        input_language = request.POST.get('input_language', 'tr')
        output_language = request.POST.get('output_language', 'tr')
        
        if action == 'text_to_voice':
            if 'document' not in request.FILES:
                return render(request, 'text_voice/text_voice.html', {'error': 'No document uploaded.'})
            uploaded_file = request.FILES['document']
            try:
                text = extract_text_from_file(uploaded_file)
                if not text.strip():
                    return render(request, 'text_voice/text_voice.html', {'error': 'Document is empty or could not be read.'})
                
                # Translate if input and output languages are different
                if input_language != output_language:
                    translator = GoogleTranslator(source=input_language, target=output_language)
                    # deep-translator handles up to 5000 chars per request, we should ideally chunk it if larger,
                    # but for basic documents this is fine. Let's chunk to be safe.
                    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                    text = " ".join([translator.translate(chunk) for chunk in chunks])
                
                # Fix for gTTS spelling out ALL CAPS words: convert to lowercase
                if output_language == 'tr':
                    text = text.replace('I', 'ı').replace('İ', 'i').lower()
                else:
                    text = text.lower()
                
                # Convert text to speech
                tts = gTTS(text=text, lang=output_language)
                
                # Use tempfile securely
                fd, path = tempfile.mkstemp(suffix=".mp3")
                try:
                    with os.fdopen(fd, 'wb') as f:
                        tts.write_to_fp(f)
                    with open(path, 'rb') as f:
                        deduct_credit(request.user)
                        response = HttpResponse(f.read(), content_type='audio/mpeg')
                        response['Content-Disposition'] = 'attachment; filename="converted_audio.mp3"'
                        return response
                finally:
                    os.remove(path)
                    
            except Exception as e:
                return render(request, 'text_voice/text_voice.html', {'error': f'Error processing document: {str(e)}'})
                
        elif action == 'voice_to_text':
            if 'audio' not in request.FILES:
                return render(request, 'text_voice/text_voice.html', {'error': 'No audio uploaded.'})
            uploaded_file = request.FILES['audio']
            
            filename = uploaded_file.name.lower()
            if not (filename.endswith('.wav') or filename.endswith('.mp3') or filename.endswith('.ogg')):
                return render(request, 'text_voice/text_voice.html', {'error': 'Only .wav, .mp3, and .ogg files are supported.'})
                
            try:
                recognizer = sr.Recognizer()
                import io
                from pydub import AudioSegment
                
                # Load audio using pydub (handles wav, mp3, ogg)
                file_format = filename.split('.')[-1]
                audio = AudioSegment.from_file(uploaded_file, format=file_format)
                
                # Map language codes to SR format
                lang_map = {
                    'tr': 'tr-TR',
                    'en': 'en-US',
                    'es': 'es-ES',
                    'de': 'de-DE',
                    'fr': 'fr-FR',
                    'ru': 'ru-RU',
                    'ar': 'ar-SA',
                    'zh-CN': 'zh-CN',
                    'hi': 'hi-IN',
                    'ja': 'ja-JP',
                    'it': 'it-IT',
                    'fa': 'fa-IR',
                    'ko': 'ko-KR',
                    'el': 'el-GR',
                    'pt': 'pt-PT',
                    'nl': 'nl-NL',
                    'pl': 'pl-PL',
                    'sv': 'sv-SE',
                    'id': 'id-ID'
                }
                sr_lang = lang_map.get(input_language, 'tr-TR')
                
                # Split audio into 30-second chunks to bypass Google Web Speech API limits and support long files
                chunk_length_ms = 30000
                chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
                
                transcripts = []
                for idx, chunk in enumerate(chunks):
                    chunk_io = io.BytesIO()
                    chunk.export(chunk_io, format="wav")
                    chunk_io.seek(0)
                    
                    try:
                        with sr.AudioFile(chunk_io) as source:
                            audio_data = recognizer.record(source)
                        chunk_text = recognizer.recognize_google(audio_data, language=sr_lang)
                        if chunk_text.strip():
                            transcripts.append(chunk_text.strip())
                    except sr.UnknownValueError:
                        # Ignore unrecognized / silent chunks
                        continue
                    except sr.RequestError as e:
                        raise e
                
                if not transcripts:
                    raise sr.UnknownValueError("Could not understand any part of the audio.")
                
                text = " ".join(transcripts)
                
                # Translate if input and output languages are different
                if input_language != output_language:
                    translator = GoogleTranslator(source=input_language, target=output_language)
                    text = translator.translate(text)
                deduct_credit(request.user)
                response = HttpResponse(text, content_type='text/plain; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="transcript.txt"'
                return response
            except sr.UnknownValueError:
                return render(request, 'text_voice/text_voice.html', {'error': 'Could not understand audio.'})
            except sr.RequestError as e:
                return render(request, 'text_voice/text_voice.html', {'error': f'Speech API error: {e}'})
            except Exception as e:
                return render(request, 'text_voice/text_voice.html', {'error': f'Error processing audio: {str(e)}'})

    return render(request, 'text_voice/text_voice.html')
