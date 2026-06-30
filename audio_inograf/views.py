from accounts.decorators import check_credits, deduct_credit
import os
import uuid
import json
import g4f
import concurrent.futures
from django.shortcuts import render
from django.conf import settings
from pydub import AudioSegment
from pydub.utils import make_chunks
import speech_recognition as sr

def parse_inograf_json(json_str):
    try:
        json_str = json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        elif json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        return json.loads(json_str.strip())
    except Exception as e:
        return None

@check_credits
def audio_inograf(request):
    if request.method == 'POST':
        if 'audio_file' not in request.FILES:
            return render(request, 'audio_inograf/audio_inograf.html', {'error': 'Please select an audio file.'})
            
        audio_file = request.FILES['audio_file']
        audio_language = request.POST.get('audio_language', 'en')
        output_language = request.POST.get('output_language', 'en')
        action = request.POST.get('action', 'infographic')
        
        session_id = str(uuid.uuid4())
        audio_ext = os.path.splitext(audio_file.name)[1]
        temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_source_{session_id}{audio_ext}')
        temp_wav_path = os.path.join(settings.BASE_DIR, f'temp_audio_{session_id}.wav')
        
        try:
            # 1. Save uploaded audio
            with open(temp_audio_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
                    
            # 2. Convert to WAV if necessary
            audio = AudioSegment.from_file(temp_audio_path)
            audio.export(temp_wav_path, format="wav")
            
            # 3. Process Audio (Chunking for long files)
            audio_wav = AudioSegment.from_file(temp_wav_path)
            chunk_length_ms = 60000 # 60 seconds
            chunks = make_chunks(audio_wav, chunk_length_ms)
            
            def process_chunk(chunk_data):
                i, chunk = chunk_data
                chunk_path = os.path.join(settings.BASE_DIR, f'temp_chunk_{session_id}_{i}.wav')
                chunk.export(chunk_path, format="wav")
                
                local_recognizer = sr.Recognizer()
                text_result = ""
                with sr.AudioFile(chunk_path) as source:
                    audio_data = local_recognizer.record(source)
                    try:
                        text = local_recognizer.recognize_google(audio_data, language=audio_language)
                        text_result = text + " "
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        text_result = f"\n[API Error: {e}]\n"
                
                try:
                    os.remove(chunk_path)
                except:
                    pass
                return i, text_result

            # 4. Parallel Transcription
            results = []
            import socket
            socket.setdefaulttimeout(30)
            
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
            try:
                futures = [executor.submit(process_chunk, (i, chunk)) for i, chunk in enumerate(chunks)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        results.append(future.result(timeout=45))
                    except concurrent.futures.TimeoutError:
                        pass
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                executor.shutdown(wait=False)
            
            # Sort by chunk index and combine
            results.sort(key=lambda x: x[0])
            full_text = "".join([x[1] for x in results]).strip()
            
            if not full_text:
                raise ValueError("Could not extract any recognizable speech from this audio.")
                
            # 5. Generate Infographic via G4F
            text_chunk = full_text[:15000]
            
            prompt = f"""
Analyze the following audio transcript and generate a structured JSON object containing a title, an overarching summary, exactly 6 key insights for an infographic, and 4 detailed chapters for a comprehensive educational e-book.

The output MUST be valid JSON matching this exact structure:
{{
  "title": "Title of the topic",
  "summary": "A broad overview of the subject.",
  "infographic": [
    {{"point": "Key Insight 1"}},
    {{"point": "Key Insight 2"}},
    {{"point": "Key Insight 3"}},
    {{"point": "Key Insight 4"}},
    {{"point": "Key Insight 5"}},
    {{"point": "Key Insight 6"}}
  ],
  "book": [
    {{"chapter_title": "Chapter 1", "content": "Full chapter content..."}},
    {{"chapter_title": "Chapter 2", "content": "Full chapter content..."}},
    {{"chapter_title": "Chapter 3", "content": "Full chapter content..."}},
    {{"chapter_title": "Chapter 4", "content": "Full chapter content..."}}
  ]
}}

Translate ALL generated content (title, summary, points, chapter_titles, and content) into the language code '{output_language}'. Return ONLY the raw JSON string, without any markdown formatting or explanations.

Audio Transcript to analyze:
{text_chunk}
"""

            result_data = None
            for attempt in range(3):
                try:

                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


                    future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=[{"role": "user", "content": prompt}])


                    response = future.result(timeout=60)


                    executor.shutdown(wait=False)
                    
                    result_data = parse_inograf_json(str(response))
                    if result_data:
                        break
                except Exception as e:
                    import time
                    time.sleep(2)
                    continue
                    
            if not result_data:
                raise ValueError("Failed to generate the infographic and e-book. The AI servers might be overloaded. Please try again.")

            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'

            icons = ['fa-lightbulb', 'fa-book-open', 'fa-rocket', 'fa-bullseye', 'fa-brain', 'fa-flag-checkered']
            infographic_data = []
            if 'infographic' in result_data:
                for i, item in enumerate(result_data['infographic']):
                    point_text = item.get('point', '')
                    title_text = "Key Insight"
                    if text_dir == 'rtl':
                        title_text = "نکته کلیدی"
                    infographic_data.append({
                        'title': f"{title_text} {i+1}",
                        'text': point_text,
                        'icon': icons[i % len(icons)]
                    })
                    
            ebook_content = ""
            if 'book' in result_data:
                for chapter in result_data['book']:
                    ebook_content += f"<h3>{chapter.get('chapter_title', '')}</h3>"
                    ebook_content += f"<p>{chapter.get('content', '')}</p>"

            deduct_credit(request.user)

            return render(request, 'audio_inograf/audio_inograf.html', {
                'success': True,
                'data': result_data,
                'infographic_data': infographic_data,
                'ebook_content': ebook_content,
                'result_type': action,
                'text_dir': text_dir,
                'output_language': output_language,
                'original_filename': audio_file.name
            })
            
        except Exception as e:
            return render(request, 'audio_inograf/audio_inograf.html', {'error': str(e)})
            
        finally:
            # Cleanup all temporary files related to this session
            import glob
            for f in glob.glob(os.path.join(settings.BASE_DIR, f'temp_*{session_id}*')):
                try:
                    os.remove(f)
                except Exception:
                    pass
                        
    return render(request, 'audio_inograf/audio_inograf.html')
