from accounts.decorators import check_credits, deduct_credit
import os
import uuid
from django.shortcuts import render
from django.conf import settings
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    from moviepy import VideoFileClip
from pydub import AudioSegment
from pydub.utils import make_chunks
import speech_recognition as sr
import concurrent.futures
import g4f
from gtts import gTTS

@check_credits
def video_to_text(request):
    if request.method == 'POST':
        if 'video_file' not in request.FILES:
            return render(request, 'video_text/video_text.html', {'error': 'Please select a video file.'})
            
        video_file = request.FILES['video_file']
        language = request.POST.get('language', 'fa-IR')
        output_language = request.POST.get('output_language', language)
        
        # Create temporary paths with UUID to avoid conflicts
        session_id = str(uuid.uuid4())
        video_ext = os.path.splitext(video_file.name)[1]
        temp_video_path = os.path.join(settings.BASE_DIR, f'temp_video_{session_id}{video_ext}')
        temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_{session_id}.wav')
        
        try:
            # 1. Save uploaded video
            with open(temp_video_path, 'wb+') as destination:
                for chunk in video_file.chunks():
                    destination.write(chunk)
                    
            # 2. Extract Audio from Video
            video = VideoFileClip(temp_video_path)
            if video.audio is None:
                video.close()
                raise ValueError("The uploaded video does not contain an audio track.")
                
            video.audio.write_audiofile(temp_audio_path, logger=None)
            video.close()
            
            # 3. Process Audio (Chunking for long files)
            audio = AudioSegment.from_file(temp_audio_path)
            chunk_length_ms = 60000 # 60 seconds
            chunks = make_chunks(audio, chunk_length_ms)
            
            def process_chunk(chunk_data):
                i, chunk = chunk_data
                chunk_path = os.path.join(settings.BASE_DIR, f'temp_chunk_{session_id}_{i}.wav')
                chunk.export(chunk_path, format="wav")
                
                local_recognizer = sr.Recognizer()
                text_result = ""
                with sr.AudioFile(chunk_path) as source:
                    audio_data = local_recognizer.record(source)
                    try:
                        text = local_recognizer.recognize_google(audio_data, language=language)
                        text_result = text + " "
                    except sr.UnknownValueError:
                        pass # Ignore silent chunks or unrecognizable parts
                    except sr.RequestError as e:
                        text_result = f"\n[API Error: {e}]\n"
                
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                return text_result

            extracted_text = ""
            chunk_data_list = list(enumerate(chunks))
            
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

            
            try:


            
                import socket


            
                socket.setdefaulttimeout(30)


            
                futures = [executor.submit(process_chunk, chunk) for chunk in chunk_data_list]


            
                for future in futures:


            
                    try:


            
                        extracted_text += future.result(timeout=45)


            
                    except concurrent.futures.TimeoutError:


            
                        extracted_text += "
[Speech Recognition Timeout: Audio chunk skipped]
"


            
                    except Exception as e:


            
                        pass


            
            except Exception as e:


            
                pass


            
            finally:


            
                executor.shutdown(wait=False)
                    
            if not extracted_text.strip():
                return render(request, 'video_text/video_text.html', {'error': 'No speech could be recognized in this video.'})
                
            final_text = extracted_text.strip()
            
            # Translate text
            if language != output_language:
                prompt = f"Translate the following text to the language code '{output_language}'. Return only the translated text, no other comments:\n\n{final_text[:15000]}"
                for attempt in range(2):
                    try:

                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


                        future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=[{"role": "user", "content": prompt}])


                        response = future.result(timeout=60)


                        executor.shutdown(wait=False)
                        translated_text = str(response).strip()
                        if translated_text.startswith('```'):
                            translated_text = translated_text.split('\n', 1)[-1]
                        if translated_text.endswith('```'):
                            translated_text = translated_text[:-3]
                        translated_text = translated_text.strip()
                        if translated_text and len(translated_text) > 5:
                            final_text = translated_text
                            break
                    except Exception as e:
                        import time
                        time.sleep(1)
                        continue

            # Ensure media dir exists
            media_dir = os.path.join(settings.BASE_DIR, 'media')
            if not os.path.exists(media_dir):
                os.makedirs(media_dir)
                
            # Create text file
            txt_filename = f"transcript_{session_id}.txt"
            txt_path = os.path.join(media_dir, txt_filename)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(final_text)

            # Generate audio file
            mp3_filename = f"audio_{session_id}.mp3"
            mp3_path = os.path.join(media_dir, mp3_filename)
            
            # Fix gTTS spelling out ALL CAPS words by converting to lowercase
            tts_text = final_text.lower()
            if output_language == 'tr':
                tts_text = tts_text.replace('I', 'ı').replace('İ', 'i')
                
            try:
                tts = gTTS(text=tts_text[:5000], lang=output_language[:2])
                tts.save(mp3_path)
            except Exception as e:
                # If gTTS fails (e.g. language not supported), we ignore audio but keep text
                mp3_filename = None

            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'

            deduct_credit(request.user)

            return render(request, 'video_text/video_text.html', {
                'success': True,
                'extracted_text': final_text,
                'original_filename': video_file.name,
                'txt_url': f"{settings.MEDIA_URL}{txt_filename}",
                'mp3_url': f"{settings.MEDIA_URL}{mp3_filename}" if mp3_filename else None,
                'text_dir': text_dir
            })
            
        except Exception as e:
            return render(request, 'video_text/video_text.html', {'error': str(e)})
            
        finally:
            # Cleanup all temporary files related to this session
            import glob
            for f in glob.glob(os.path.join(settings.BASE_DIR, f'temp_*{session_id}*')):
                try:
                    os.remove(f)
                except Exception:
                    pass
    return render(request, 'video_text/video_text.html')