from accounts.decorators import check_credits, deduct_credit
import os
import uuid
import json
import re
from django.shortcuts import render
from django.conf import settings
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip
from pydub import AudioSegment
from pydub.utils import make_chunks
import speech_recognition as sr
import concurrent.futures
from g4f.client import Client
import g4f
from collections import Counter
from yt_dlp import YoutubeDL

STOP_WORDS = set([
    # Persian
    'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'برای', 'آن', 'یک', 'خود', 'تا', 'بر', 'یا', 'هم', 'نیز', 'من', 'تو', 'او', 'ما', 'شما', 'آنها', 'می', 'های', 'ها', 'دارد', 'شده', 'بود', 'کرد', 'کند', 'باشد', 'اما', 'اگر', 'پس', 'چه', 'چون', 'روی', 'زیر', 'بین', 'همه', 'هیچ', 'هر', 'دو', 'سه', 'خیلی', 'بسیار', 'دیگر', 'فقط', 'شاید', 'باید', 'البته', 'چند', 'مثل', 'همان', 'همین', 'اینکه', 'وقتی', 'توی', 'اون', 'اینا', 'اونا', 'رو', 'میشه', 'باشه', 'دارم', 'داره', 'داریم', 'دارند', 'است.', 'دارد.', 'باشند', 'نیست', 'ولی', 'پس', 'اما', 'شما', 'ما', 'اون', 'این', 'کردن', 'دادن', 'بودن', 'داشتن', 'شدن', 'رفتن', 'آمدن', 'ها', 'رو', 'تو', 'که', 'از', 'به', 'با', 'تا', 'برای', 'در', 'و', 'یا', 'هم', 'همین', 'همان', 'مگر', 'جز', 'الا', 'بلکه', 'اما', 'ولی', 'لیک', 'ولیکن', 'بنابراین', 'پس', 'لذا', 'مبادا', 'چون', 'زیرا', 'که', 'اگر', 'ار', 'گر', 'چه', 'چون', 'تا',
    # English
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
])

def extract_keywords(text, n=5):
    words = re.findall(r'\b\w+\b', text.lower())
    filtered_words = [w for w in words if len(w) > 3 and w not in STOP_WORDS and not w.isdigit()]
    counter = Counter(filtered_words)
    return [word for word, count in counter.most_common(n)]

def extract_key_points(text, output_lang="en"):
    try:
        prompt_text = text[:15000]
        prompt = f"""You are an expert educational content creator and translator.
Please deeply analyze the following text and extract its CORE educational framework.
If the text explicitly mentions a specific number of rules, steps, or laws, you MUST find and extract those exact points as the main focus of your infographic.
Output EXACTLY 6 points.
Format your output as a JSON array, strictly like this:
[
  {{
    "title": "Short catchy title",
    "text": "Detailed, cohesive educational explanation under 200 characters.",
    "icon": "fa-lightbulb" 
  }}
]
Rules:
1. ONLY output raw JSON. Do not use markdown blocks.
2. Use FontAwesome 6 free solid icons.
3. The title and text MUST be translated and written ENTIRELY in the language code: {output_lang}.

Text:
{prompt_text}"""
        
        for attempt in range(3):
            try:

                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


                future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=[{"role": "user", "content": prompt}])


                response = future.result(timeout=60)


                executor.shutdown(wait=False)
                
                response_text = str(response).strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                    
                data = json.loads(response_text.strip())
                if isinstance(data, list) and len(data) > 0:
                    return data[:6]
            except Exception as e:
                import time
                time.sleep(2)
                continue
    except Exception as e:
        pass

    text = text.replace('؛', '.').replace('\n', '. ').replace('?', '.').replace('!', '.')
    if text.count('.') < 5:
        words = text.split()
        text = ""
        for i, w in enumerate(words):
            text += w + " "
            if i > 0 and i % 15 == 0:
                text += ". "
                
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 25]
    
    if not sentences:
        return [
            {"title": "Video Processed", "text": "The video was analyzed but the content was too short or unrecognizable to generate an infographic.", "icon": "fa-video"},
            {"title": "No Content", "text": "We were able to extract audio, but text summarization failed.", "icon": "fa-file-lines"}
        ]

    keywords = extract_keywords(text, n=6)
    selected_items = []
    used_indices = set()
    
    if sentences:
        selected_items.append({
            'title': "شروع مطلب / Intro",
            'text': sentences[0],
            'icon': 'fa-play'
        })
        used_indices.add(0)
        
    for kw in keywords:
        if len(selected_items) >= 5:
            break
        for i, s in enumerate(sentences):
            if i not in used_indices and kw in s.lower():
                selected_items.append({
                    'title': f"کلیدواژه: {kw.capitalize()}",
                    'text': s,
                    'icon': 'fa-star'
                })
                used_indices.add(i)
                break
                
    last_idx = len(sentences) - 1
    if last_idx > 0 and last_idx not in used_indices and len(selected_items) < 6:
        selected_items.append({
            'title': "نتیجه‌گیری / Conclusion",
            'text': sentences[last_idx],
            'icon': 'fa-check-double'
        })
        
    if len(selected_items) < 6:
        for i, s in enumerate(sentences):
            if i not in used_indices:
                selected_items.append({
                    'title': "نکته مهم / Key Point",
                    'text': s,
                    'icon': 'fa-lightbulb'
                })
                used_indices.add(i)
                if len(selected_items) >= 6:
                    break

    icons = ['fa-lightbulb', 'fa-book-open', 'fa-rocket', 'fa-bullseye', 'fa-brain', 'fa-flag-checkered']
    
    infographic_data = []
    for i, item in enumerate(selected_items[:6]):
        text_content = item['text']
        if len(text_content) > 250:
            text_content = text_content[:247] + "..."
            
        infographic_data.append({
            'text': text_content + ("." if not text_content.endswith('.') else ""),
            'title': item['title'],
            'icon': icons[i % len(icons)],
        })
        
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target=output_lang)
        for item in infographic_data:
            if item.get('title'):
                item['title'] = translator.translate(item['title'])
            if item.get('text'):
                item['text'] = translator.translate(item['text'])
    except Exception as e:
        print(f"Fallback translation failed: {e}")
        
    return infographic_data

def generate_ebook_content(text, output_lang="en"):
    try:
        prompt_text = text[:15000]
        prompt = f"""You are an expert author, educational content creator, and translator.
Please deeply analyze the following text and convert it into a comprehensive, professional, and accurate Educational E-Book chapter.
Your output MUST be entirely in HTML format, structured specifically for an E-Book page. 
Use these tags:
- <h2> for the main E-Book title
- <h3> for section/chapter headings
- <p> for detailed paragraphs
- <ul> and <li> for any lists or bullet points
- <strong> for emphasis
Rules:
1. DO NOT include <html>, <head>, or <body> tags. Just the content tags.
2. DO NOT use markdown code blocks like ```html. Output raw HTML.
3. Ensure the E-book is highly detailed, well-written, and logically structured (Introduction, Main Chapters, Conclusion).
4. The output MUST be translated and written ENTIRELY in the language code: {output_lang}.

Text:
{prompt_text}"""
        
        for attempt in range(3):
            try:

                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)


                future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=[{"role": "user", "content": prompt}])


                response = future.result(timeout=60)


                executor.shutdown(wait=False)
                
                response_text = str(response).strip()
                if response_text.startswith('```html'):
                    response_text = response_text[7:]
                elif response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                    
                if len(response_text) > 100:
                    return response_text.strip()
            except Exception as e:
                import time
                time.sleep(2)
                continue
    except Exception as e:
        pass

    text_clean = text.replace('؛', '.').replace('\n', '. ').replace('?', '.').replace('!', '.')
    if text_clean.count('.') < 5:
        words = text_clean.split()
        text_clean = ""
        for i, w in enumerate(words):
            text_clean += w + " "
            if i > 0 and i % 15 == 0:
                text_clean += ". "
                
    sentences = [s.strip() for s in text_clean.split('.') if len(s.strip()) > 20]
    
    if not sentences:
        return "<h2>E-Book Generation Failed</h2><p>The uploaded video was too short or its audio could not be analyzed.</p>"
        
    title_str = "Educational E-Book"
    intro_str = "Introduction"
    main_str = "Main Content"
    conc_str = "Conclusion"
    
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target=output_lang)
        title_str = translator.translate(title_str)
        intro_str = translator.translate(intro_str)
        main_str = translator.translate(main_str)
        conc_str = translator.translate(conc_str)
        
        sentences = [translator.translate(s) for s in sentences[:10]]
    except Exception as e:
        print("Fallback E-Book translation failed:", e)

    html = f"<h2>{title_str}</h2>"
    html += f"<h3>{intro_str}</h3>"
    html += f"<p>{sentences[0]}</p>"
    
    html += f"<h3>{main_str}</h3><p>"
    for s in sentences[1:-1]:
        html += f"{s}. "
    html += "</p>"
    
    if len(sentences) > 1:
        html += f"<h3>{conc_str}</h3>"
        html += f"<p>{sentences[-1]}</p>"
        
    return html

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    match = re.match(youtube_regex, url)
    return bool(match)

@check_credits
def youtube_to_image(request):
    if request.method == 'POST':
        youtube_url = request.POST.get('youtube_url', '').strip()
        video_language = request.POST.get('video_language', 'en')
        output_language = request.POST.get('output_language', video_language)
        
        if not youtube_url:
            return render(request, 'youtube_inograf/youtube_inograf.html', {'error': 'Please provide a YouTube URL.'})
            
        if not is_valid_youtube_url(youtube_url):
            return render(request, 'youtube_inograf/youtube_inograf.html', {'error': 'Invalid YouTube URL. Please enter a valid link.'})
            
        session_id = str(uuid.uuid4())
        temp_download_path = os.path.join(settings.BASE_DIR, f'temp_yti_dl_{session_id}.m4a')
        temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_yti_{session_id}.wav')
        
        try:
            from youtube_utils import extract_youtube_transcript
            extracted_text = extract_youtube_transcript(youtube_url, video_language) or ""
            
            if not extracted_text.strip():
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
                    raise Exception("Failed to download audio from YouTube.")
                    
                clip = AudioFileClip(temp_download_path)
                clip.write_audiofile(temp_audio_path, logger=None)
                clip.close()
                
                audio = AudioSegment.from_file(temp_audio_path)
                chunk_length_ms = 60000 
                chunks = make_chunks(audio, chunk_length_ms)
                
                def process_chunk(chunk_data):
                    i, chunk = chunk_data
                    chunk_path = f"{temp_audio_path}_chunk{i}.wav"
                    chunk.export(chunk_path, format="wav")
                    
                    local_recognizer = sr.Recognizer()
                    text_result = ""
                    with sr.AudioFile(chunk_path) as source:
                        audio_data = local_recognizer.record(source)
                        try:
                            text = local_recognizer.recognize_google(audio_data, language=video_language)
                            text_result = text + " "
                        except sr.UnknownValueError:
                            pass
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

    
                
                            extracted_text += "\n[Speech Recognition Timeout: Audio chunk skipped]\n"

    
                
                        except Exception as e:

    
                
                            pass

    
                
                except Exception as e:

    
                
                    pass

    
                
                finally:

    
                
                    executor.shutdown(wait=False)
                    
            if not extracted_text.strip():
                return render(request, 'youtube_inograf/youtube_inograf.html', {'error': 'No speech could be recognized in this video.'})
                
            action = request.POST.get('action', 'infographic')
            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
            
            if action == 'ebook':
                ebook_content = generate_ebook_content(extracted_text.strip(), output_lang=output_language)
                deduct_credit(request.user)
                return render(request, 'youtube_inograf/youtube_inograf.html', {
                    'success': True,
                    'result_type': 'ebook',
                    'ebook_content': ebook_content,
                    'original_url': youtube_url,
                    'text_dir': text_dir
                })
            else:
                infographic_data = extract_key_points(extracted_text.strip(), output_lang=output_language)
                deduct_credit(request.user)
                return render(request, 'youtube_inograf/youtube_inograf.html', {
                    'success': True,
                    'result_type': 'infographic',
                    'infographic_data': infographic_data,
                    'original_url': youtube_url,
                    'text_dir': text_dir
                })
                
        except Exception as e:
            return render(request, 'youtube_inograf/youtube_inograf.html', {'error': f'Error processing video: {str(e)}'})
            
        finally:
            if os.path.exists(temp_download_path):
                try: os.remove(temp_download_path)
                except: pass
            if os.path.exists(temp_audio_path):
                try: os.remove(temp_audio_path)
                except: pass

    return render(request, 'youtube_inograf/youtube_inograf.html')