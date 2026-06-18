import os

APPS = ['pic_text', 'web_inograf', 'audio_inograf', 'ai_quiz', 'chat_doc', 'data_chart', 'text_voice', 'video_text', 'text_inograf', 'video_inograf', 'youtube_inograf', 'youtube_text']

for app in APPS:
    view_path = f"d:/Converter/{app}/views.py"
    if not os.path.exists(view_path): continue
    with open(view_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "accounts.decorators" in content:
        continue
        
    # Prepend imports
    content = "from accounts.decorators import check_credits, deduct_credit\n" + content
    
    # Add decorator to main view. Main view is always def <app_name>(request):
    content = content.replace(f"def {app}(request):", f"@check_credits\ndef {app}(request):")
    
    # Write back
    with open(view_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Decorators applied!")
