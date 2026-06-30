from accounts.decorators import check_credits, deduct_credit
import os
import uuid
from django.shortcuts import render
from django.conf import settings
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip
from pydub import AudioSegment
from pydub.utils import make_chunks
import speech_recognition as sr
from yt_dlp import YoutubeDL
import re
import concurrent.futures
from g4f.client import Client
import g4f

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    match = re.match(youtube_regex, url)
    return bool(match)

@check_credits
def youtube_to_text(request):
    if request.method == 'POST':
        youtube_url = request.POST.get('youtube_url', '').strip()
        video_language = request.POST.get('video_language', request.POST.get('language', 'fa-IR'))
        output_language = request.POST.get('output_language', video_language)
        
        if not youtube_url:
            return render(request, 'youtube_text/youtube_text.html', {'error': 'Please provide a YouTube URL.'})
            
        if not is_valid_youtube_url(youtube_url):
            return render(request, 'youtube_text/youtube_text.html', {'error': 'Invalid YouTube URL. Please enter a valid link.'})
        
        session_id = str(uuid.uuid4())
        temp_download_path = os.path.join(settings.BASE_DIR, f'temp_yt_dl_{session_id}.m4a')
        temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_{session_id}.wav')
        
        try:
            from youtube_utils import extract_youtube_transcript
            extracted_text = extract_youtube_transcript(youtube_url, video_language) or ""
            
            if not extracted_text.strip():
                # 1. Download YouTube Audio using yt-dlp
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio',
                    'outtmpl': temp_download_path,
                    'quiet': True,
                    'no_warnings': True,
                    'nopart': True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                    
                if not os.path.exists(temp_download_path):
                    raise ValueError("Failed to download audio from the YouTube video.")
    
                # 2. Convert Audio to WAV using moviepy
                clip = AudioFileClip(temp_download_path)
                clip.write_audiofile(temp_audio_path, logger=None)
                clip.close()
                
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
                            text = local_recognizer.recognize_google(audio_data, language=video_language)
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
                return render(request, 'youtube_text/youtube_text.html', {'error': 'No speech could be recognized in this video.'})
                
            final_text = extracted_text.strip()
            
            if video_language != output_language:
                prompt = f"Translate the following text to the language code '{output_language}'. Return only the translated text, no other comments:\n\n{final_text[:15000]}"
                for attempt in range(3):
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
                        print(f"Translation failed on attempt {attempt+1}: {e}")
                        import time
                        time.sleep(2)
                        continue
                    
            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
                
            deduct_credit(request.user)
                
            return render(request, 'youtube_text/youtube_text.html', {
                'success': True,
                'extracted_text': final_text,
                'original_url': youtube_url,
                'text_dir': text_dir
            })
            
        except Exception as e:
            return render(request, 'youtube_text/youtube_text.html', {'error': f'Error processing video: {str(e)}'})
            
        finally:
            # Cleanup all temporary files related to this session
            import glob
            for f in glob.glob(os.path.join(settings.BASE_DIR, f'temp_*{session_id}*')):
                try:
                    os.remove(f)
                except Exception:
                    pass
                
    return render(request, 'youtube_text/youtube_text.html')