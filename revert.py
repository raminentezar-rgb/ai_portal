import os
import re

base_dir = r'd:\Converter'
files_to_check = [
    'audio_inograf/views.py',
    'chat_doc/views.py',
    'pic_text/views.py',
    'text_inograf/views.py',
    'video_inograf/views.py',
    'video_text/views.py',
    'web_inograf/views.py',
    'youtube_inograf/views.py',
    'youtube_text/views.py',
]

pattern = re.compile(
    r'[ \t]*import concurrent\.futures\n[ \t]*with concurrent\.futures\.ThreadPoolExecutor\(max_workers=1\) as executor:\n([ \t]*)future = executor\.submit\(g4f\.ChatCompletion\.create,\n([ \t]*)model=g4f\.models\.default,\n([ \t]*)messages=messages\n[ \t]*\)\n[ \t]*response = future\.result\(timeout=\d+\)'
)

pattern_prompt = re.compile(
    r'[ \t]*import concurrent\.futures\n[ \t]*with concurrent\.futures\.ThreadPoolExecutor\(max_workers=1\) as executor:\n([ \t]*)future = executor\.submit\(g4f\.ChatCompletion\.create,\n([ \t]*)model=g4f\.models\.default,\n([ \t]*)messages=\[\{"role": "user", "content": prompt\}\]\n[ \t]*\)\n[ \t]*response = future\.result\(timeout=\d+\)'
)

for fpath in files_to_check:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the prompt-based ones
        new_content = pattern_prompt.sub(
            r'\1response = g4f.ChatCompletion.create(\n\2model=g4f.models.default,\n\3messages=[{"role": "user", "content": prompt}]\n\1)',
            content
        )
        
        # Replace the messages-based ones
        new_content = pattern.sub(
            r'\1response = g4f.ChatCompletion.create(\n\2model=g4f.models.default,\n\3messages=messages\n\1)',
            new_content
        )
        
        if new_content != content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Reverted g4f timeouts in {fpath}')
