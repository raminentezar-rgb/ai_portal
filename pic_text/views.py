from accounts.decorators import check_credits, deduct_credit
import os
import tempfile
import base64
import requests
from django.shortcuts import render
from django.http import HttpResponse
from gtts import gTTS
import g4f

def extract_text_from_image(image_file, lang_code='eng'):
    try:
        img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        b64_string = f"data:image/jpeg;base64,{img_b64}"

        payload = {
            'base64Image': b64_string,
            'apikey': 'helloworld',
            'language': lang_code,
            'isOverlayRequired': False
        }
        r = requests.post('https://api.ocr.space/parse/image', data=payload)
        result = r.json()
        
        if result.get('IsErroredOnProcessing'):
            return None, result.get('ErrorMessage', ['Error processing image'])[0]
            
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return None, "No text found in the image."
            
        extracted_text = parsed_results[0].get('ParsedText', '')
        return extracted_text, None
    except Exception as e:
        return None, str(e)

@check_credits
def pic_text(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        source_language = request.POST.get('source_language', 'en')
        output_language = request.POST.get('output_language', source_language)
        
        # Mapping frontend lang codes to OCR.space lang codes
        ocr_lang_map = {
            'en': 'eng', 'tr': 'tur', 'es': 'spa', 'de': 'ger',
            'fr': 'fre', 'ru': 'rus', 'ar': 'ara', 'fa': 'ara',
            'ko': 'kor', 'ja': 'jpn', 'it': 'ita', 'zh-CN': 'chs',
            'hi': 'eng', 'pt': 'por', 'nl': 'dut', 'pl': 'pol',
            'sv': 'swe', 'el': 'gre', 'id': 'eng'
        }
        
        if action == 'extract':
            if 'image_file' not in request.FILES:
                return render(request, 'pic_text/pic_text.html', {'error': 'No image uploaded.'})
                
            uploaded_file = request.FILES['image_file']
            ocr_lang = ocr_lang_map.get(source_language, 'eng')
            
            extracted_text, error = extract_text_from_image(uploaded_file, lang_code=ocr_lang)
            
            if error:
                return render(request, 'pic_text/pic_text.html', {'error': error})
                
            if not extracted_text or not extracted_text.strip():
                return render(request, 'pic_text/pic_text.html', {'error': 'Could not extract any text from the provided image.'})
                
            extracted_text = extracted_text.strip()
            
            if source_language != output_language:
                prompt = f"Translate the following text to the language code '{output_language}'. Return only the translated text, no other comments:\n\n{extracted_text[:15000]}"
                for attempt in range(3):
                    try:
                        import concurrent.futures

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
                            extracted_text = translated_text
                            break
                    except Exception as e:
                        import time
                        time.sleep(2)
                        continue
                        
            text_dir = 'rtl' if output_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
                
            deduct_credit(request.user)
                
            return render(request, 'pic_text/pic_text.html', {
                'success': True,
                'extracted_text': extracted_text,
                'source_language': source_language,
                'output_language': output_language,
                'text_dir': text_dir,
                'original_filename': uploaded_file.name
            })
            
        elif action == 'text_download':
            extracted_text = request.POST.get('extracted_text', '')
            response = HttpResponse(extracted_text, content_type='text/plain; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="extracted_text.txt"'
            return response
            
        elif action == 'voice_download':
            extracted_text = request.POST.get('extracted_text', '')
            try:
                # Fix for gTTS spelling out ALL CAPS words: convert to lowercase
                tts_text = extracted_text
                if output_language == 'tr':
                    tts_text = tts_text.replace('I', 'ı').replace('İ', 'i').lower()
                else:
                    tts_text = tts_text.lower()
                
                tts = gTTS(text=tts_text, lang=output_language)
                
                fd, path = tempfile.mkstemp(suffix=".mp3")
                try:
                    with os.fdopen(fd, 'wb') as f:
                        tts.write_to_fp(f)
                    
                    with open(path, 'rb') as f:
                        response = HttpResponse(f.read(), content_type='audio/mpeg')
                        response['Content-Disposition'] = 'attachment; filename="audio.mp3"'
                        return response
                finally:
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
            except Exception as e:
                return render(request, 'pic_text/pic_text.html', {
                    'error': f'Voice generation failed: {str(e)}',
                    'success': True,
                    'extracted_text': extracted_text,
                    'source_language': source_language
                })
                
    return render(request, 'pic_text/pic_text.html')