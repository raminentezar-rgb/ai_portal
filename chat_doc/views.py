from accounts.decorators import check_credits, deduct_credit
import json
import g4f
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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

@check_credits
def chat_doc(request):
    if request.method == 'POST':
        source_text = request.POST.get('source_text', '').strip()
        
        if 'document' in request.FILES and request.FILES['document'].name:
            try:
                source_text = extract_text_from_document(request.FILES['document'])
            except Exception as e:
                return render(request, 'chat_doc/chat_doc.html', {'error': f'Failed to read document: {str(e)}'})
                
        if not source_text or len(source_text) < 20:
            return render(request, 'chat_doc/chat_doc.html', {'error': 'Not enough text provided.'})
            
        # Limit text to 15000 chars to avoid prompt limits
        source_text = source_text[:15000]
        
        deduct_credit(request.user)
        
        return render(request, 'chat_doc/chat_doc.html', {
            'success': True,
            'document_context': source_text
        })
        
    return render(request, 'chat_doc/chat_doc.html')

@csrf_exempt
def chat_message(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            context = data.get('context', '')
            chat_history = data.get('history', [])
            user_message = data.get('message', '')
            
            system_prompt = f"""
You are an expert AI Assistant answering questions strictly based on the provided document.
Document Context:
{context}

Answer the user's questions truthfully. If the answer is not in the document, politely inform the user that the document doesn't contain that information.
"""

            messages = [{"role": "system", "content": system_prompt}]
            
            # Add last 6 messages from history to keep context small
            for msg in chat_history[-6:]:
                messages.append({"role": msg['role'], "content": msg['content']})
                
            messages.append({"role": "user", "content": user_message})

            response = g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=messages
            )
            
            return JsonResponse({'status': 'success', 'reply': str(response)})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
