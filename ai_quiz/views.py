from accounts.decorators import check_credits, deduct_credit
import json
import g4f
import concurrent.futures
from django.shortcuts import render
import PyPDF2
import docx

def extract_text_from_document(uploaded_file):
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

def parse_quiz_json(json_str):
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
def ai_quiz(request):
    if request.method == 'POST':
        source_text = request.POST.get('source_text', '').strip()
        quiz_language = request.POST.get('quiz_language', 'en')
        
        # If file is uploaded, extract text and override source_text
        if 'document' in request.FILES and request.FILES['document'].name:
            try:
                source_text = extract_text_from_document(request.FILES['document'])
            except Exception as e:
                return render(request, 'ai_quiz/ai_quiz.html', {'error': f'Failed to read document: {str(e)}'})
                
        if not source_text or len(source_text) < 50:
            return render(request, 'ai_quiz/ai_quiz.html', {'error': 'Not enough text provided to generate a quiz (minimum 50 characters).'})
            
        text_chunk = source_text[:10000]
        
        prompt = f"""
Analyze the following educational text and generate an interactive Multiple-Choice Quiz to test the user's knowledge.
Generate exactly 5 to 7 high-quality questions.

The output MUST be valid JSON matching this exact structure:
{{
  "quiz_title": "Title of the Quiz based on the subject",
  "questions": [
    {{
      "question": "The question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 1,
      "explanation": "Why this answer is correct."
    }}
  ]
}}
Note: "correct_answer_index" must be an integer from 0 to 3 corresponding to the correct option in the "options" array.

Translate ALL generated content (title, questions, options, explanation) into the language code '{quiz_language}'. Return ONLY the raw JSON string.

Text to analyze:
{text_chunk}
"""

        def fetch_g4f():
            return g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[{"role": "user", "content": prompt}]
            )

        quiz_data = None
        for attempt in range(2):
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(fetch_g4f)
                response = future.result(timeout=30)
                
                quiz_data = parse_quiz_json(str(response))
                if quiz_data and "questions" in quiz_data:
                    break
            except concurrent.futures.TimeoutError:
                continue
            except Exception as e:
                import time
                time.sleep(1)
                continue
                
        if not quiz_data:
            return render(request, 'ai_quiz/ai_quiz.html', {
                'error': 'Failed to generate the quiz. The AI servers might be overloaded. Please try again.'
            })
            
        text_dir = 'rtl' if quiz_language in ['fa', 'ar', 'fa-IR'] else 'ltr'
        
        # We need to serialize the quiz data to JSON string to embed in frontend JS
        quiz_json_string = json.dumps(quiz_data)
        
        deduct_credit(request.user)
        
        return render(request, 'ai_quiz/ai_quiz.html', {
            'success': True,
            'quiz_data': quiz_data,
            'quiz_json_string': quiz_json_string,
            'text_dir': text_dir,
            'quiz_language': quiz_language
        })
        
    return render(request, 'ai_quiz/ai_quiz.html')
