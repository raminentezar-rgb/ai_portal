import os
import re

APPS = ['pic_text', 'web_inograf', 'audio_inograf', 'ai_quiz', 'chat_doc', 'data_chart', 'text_voice', 'video_text', 'text_inograf', 'video_inograf', 'youtube_inograf', 'youtube_text']

for app in APPS:
    view_path = f"d:/Converter/{app}/views.py"
    if not os.path.exists(view_path): continue
    
    with open(view_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "deduct_credit(request.user)" in content:
        print(f"Already patched: {app}")
        continue
        
    pattern = re.compile(r"(\s+)(return render\(\s*request\s*,\s*['\"]" + app + r"/" + app + r"\.html['\"]\s*,\s*\{\s*['\"]success['\"]\s*:\s*True)")
    
    new_content, count = pattern.subn(r"\1deduct_credit(request.user)\1\2", content)
    
    if count > 0:
        with open(view_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Patched successfully: {app} ({count} replacements)")
    else:
        print(f"FAILED TO PATCH: {app}")
