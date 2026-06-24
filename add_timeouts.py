import os
import re

base_dir = r'd:\Converter'
files = [
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

pattern1 = re.compile(
    r'(\s+)response = g4f\.ChatCompletion\.create\(\n\s+model=g4f\.models\.default,\n\s+messages=\[\{"role": "user", "content": prompt\}\]\n\s+\)'
)
replacement1 = r'''\1import concurrent.futures
\1with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
\1    future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=[{"role": "user", "content": prompt}])
\1    response = future.result(timeout=60)'''

pattern2 = re.compile(
    r'(\s+)response = g4f\.ChatCompletion\.create\(\n\s+model=g4f\.models\.default,\n\s+messages=messages\n\s+\)'
)
replacement2 = r'''\1import concurrent.futures
\1with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
\1    future = executor.submit(g4f.ChatCompletion.create, model=g4f.models.default, messages=messages)
\1    response = future.result(timeout=60)'''

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = pattern1.sub(replacement1, content)
        new_content = pattern2.sub(replacement2, new_content)
        
        if new_content != content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Added timeout to {fpath}')
