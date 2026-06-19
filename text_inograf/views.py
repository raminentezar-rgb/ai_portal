from accounts.decorators import check_credits, deduct_credit
import os
import uuid
import json
import re
from django.shortcuts import render
from django.conf import settings
import PyPDF2
import docx
import concurrent.futures
from g4f.client import Client
import g4f
from collections import Counter

STOP_WORDS = set([
    # Persian
    'و', 'در', 'به', 'از', 'که', 'این', 'را', 'با', 'است', 'برای', 'آن', 'یک', 'خود', 'تا', 'بر', 'یا', 'هم', 'نیز', 'من', 'تو', 'او', 'ما', 'شما', 'آنها', 'می', 'های', 'ها', 'دارد', 'شده', 'بود', 'کرد', 'کند', 'باشد', 'اما', 'اگر', 'پس', 'چه', 'چون', 'روی', 'زیر', 'بین', 'همه', 'هیچ', 'هر', 'دو', 'سه', 'خیلی', 'بسیار', 'دیگر', 'فقط', 'شاید', 'باید', 'البته', 'چند', 'مثل', 'همان', 'همین', 'اینکه', 'وقتی', 'توی', 'اون', 'اینا', 'اونا', 'رو', 'میشه', 'باشه', 'دارم', 'داره', 'داریم', 'دارند', 'است.', 'دارد.', 'باشند', 'نیست', 'ولی', 'پس', 'اما', 'شما', 'ما', 'اون', 'این', 'کردن', 'دادن', 'بودن', 'داشتن', 'شدن', 'رفتن', 'آمدن', 'ها', 'رو', 'تو', 'که', 'از', 'به', 'با', 'تا', 'برای', 'در', 'و', 'یا', 'هم', 'همین', 'همان', 'مگر', 'جز', 'الا', 'بلکه', 'اما', 'ولی', 'لیک', 'ولیکن', 'بنابراین', 'پس', 'لذا', 'مبادا', 'چون', 'زیرا', 'که', 'اگر', 'ار', 'گر', 'چه', 'چون', 'تا',
    # English
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
])

def extract_text_from_file(uploaded_file):
    filename = uploaded_file.name.lower()
    text = ""
    if filename.endswith('.txt'):
        text = uploaded_file.read().decode('utf-8', errors='ignore')
    elif filename.endswith('.pdf'):
        reader = PyPDF2.PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif filename.endswith('.docx'):
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

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
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(g4f.ChatCompletion.create, 
                        model=g4f.models.default, 
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response = future.result(timeout=25)
                
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

    text_clean = text.replace('؛', '.').replace('\n', '. ').replace('?', '.').replace('!', '.')
    if text_clean.count('.') < 5:
        words = text_clean.split()
        text_clean = ""
        for i, w in enumerate(words):
            text_clean += w + " "
            if i > 0 and i % 15 == 0:
                text_clean += ". "
                
    sentences = [s.strip() for s in text_clean.split('.') if len(s.strip()) > 25]
    
    if not sentences:
        return [
            {"title": "File Processed", "text": "The file was analyzed but the content was too short or unrecognizable to generate an infographic.", "icon": "fa-file"},
            {"title": "No Content", "text": "We were able to extract text, but summarization failed.", "icon": "fa-file-lines"}
        ]

    keywords = extract_keywords(text_clean, n=6)
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
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(g4f.ChatCompletion.create, 
                        model=g4f.models.default, 
                        messages=[{"role": "user", "content": prompt}]
                    )
                    response = future.result(timeout=45)
                
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
        return "<h2>E-Book Generation Failed</h2><p>The uploaded text was too short or could not be analyzed.</p>"
        
    html = f"<h2>Educational E-Book</h2>"
    html += "<h3>Introduction</h3>"
    html += f"<p>{sentences[0]}</p>"
    
    html += "<h3>Main Content</h3><p>"
    for s in sentences[1:-1]:
        html += f"{s}. "
    html += "</p>"
    
    if len(sentences) > 1:
        html += "<h3>Conclusion</h3>"
        html += f"<p>{sentences[-1]}</p>"
        
    return html

@check_credits
def text_to_image(request):
    if request.method == 'POST':
        if 'document' not in request.FILES:
            return render(request, 'text_inograf/text_inograf.html', {'error': 'No document uploaded.'})
        
        uploaded_file = request.FILES['document']
        source_language = request.POST.get('source_language', 'en')
        output_language = request.POST.get('output_language', source_language)
        
        try:
            text = extract_text_from_file(uploaded_file)
            if not text.strip():
                return render(request, 'text_inograf/text_inograf.html', {'error': 'Document is empty or could not be read.'})
            
            final_text = text.strip()
            
            # Note: We don't necessarily need to translate the whole text here because 
            # the G4F AI prompt for E-book and Infographic handles the translation internally.
            # However, if NLP fallback happens, it won't be translated. But G4F is primary.

            action = request.POST.get('action', 'infographic')
            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
            
            if action == 'ebook':
                ebook_content = generate_ebook_content(final_text, output_lang=output_language)
                deduct_credit(request.user)
                return render(request, 'text_inograf/text_inograf.html', {
                    'success': True,
                    'result_type': 'ebook',
                    'ebook_content': ebook_content,
                    'original_filename': uploaded_file.name,
                    'text_dir': text_dir
                })
            else:
                infographic_data = extract_key_points(final_text, output_lang=output_language)
                deduct_credit(request.user)
                return render(request, 'text_inograf/text_inograf.html', {
                    'success': True,
                    'result_type': 'infographic',
                    'infographic_data': infographic_data,
                    'original_filename': uploaded_file.name,
                    'text_dir': text_dir
                })
            
        except Exception as e:
            return render(request, 'text_inograf/text_inograf.html', {'error': f'Error processing document: {str(e)}'})
            
    return render(request, 'text_inograf/text_inograf.html')
