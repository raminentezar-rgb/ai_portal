from accounts.decorators import check_credits, deduct_credit
import requests
from bs4 import BeautifulSoup
import g4f
import json
import concurrent.futures
from django.shortcuts import render

def extract_text_from_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts, styles, nav, footer, etc to get clean content
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        return text, None
    except Exception as e:
        return None, str(e)

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
def web_inograf(request):
    if request.method == 'POST':
        url = request.POST.get('url')
        output_language = request.POST.get('output_language', 'en')
        action = request.POST.get('action', 'infographic')
        
        if not url:
            return render(request, 'web_inograf/web_inograf.html', {'error': 'No URL provided.'})
            
        extracted_text, error = extract_text_from_url(url)
        
        if error:
            return render(request, 'web_inograf/web_inograf.html', {'error': f'Could not scrape website: {error}'})
            
        if not extracted_text or len(extracted_text) < 50:
            return render(request, 'web_inograf/web_inograf.html', {'error': 'Not enough text found on this webpage.'})
            
        # We limit the text size to avoid exceeding token limits
        text_chunk = extracted_text[:15000]
        
        prompt = f"""
Analyze the following text scraped from a webpage and generate a structured JSON object containing a title, an overarching summary, exactly 6 key insights for an infographic, and 4 detailed chapters for a comprehensive educational e-book.

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

CRITICAL INSTRUCTION: You MUST translate ALL generated content (title, summary, points, chapter_titles, and content) into the language corresponding to the language code '{output_language}'. For example, if it is 'fa', write EVERYTHING in Persian. If it is 'tr', write EVERYTHING in Turkish. Return ONLY the raw JSON string, without any markdown formatting or explanations. Do not output anything in English unless the requested language is 'en'.

Text to analyze:
{text_chunk}
"""

        result_data = None
        for attempt in range(3):
            try:
                import concurrent.futures

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
            return render(request, 'web_inograf/web_inograf.html', {
                'error': 'Failed to generate the infographic and e-book. The AI servers might be overloaded. Please try again.'
            })
            
        text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
        
        icons = ['fa-lightbulb', 'fa-book-open', 'fa-rocket', 'fa-bullseye', 'fa-brain', 'fa-flag-checkered']
        infographic_data = []
        if 'infographic' in result_data:
            for i, item in enumerate(result_data['infographic']):
                point_text = item.get('point', '')
                title_text = "Key Insight"
                # If language is Persian/Arabic, change default title
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
        
        return render(request, 'web_inograf/web_inograf.html', {
            'success': True,
            'data': result_data,
            'infographic_data': infographic_data,
            'ebook_content': ebook_content,
            'result_type': action,
            'text_dir': text_dir,
            'output_language': output_language,
            'original_url': url
        })
        
    return render(request, 'web_inograf/web_inograf.html')
