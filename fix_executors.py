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

def replace_with_block(content):
    # Fix max_workers=1 (g4f)
    pattern1 = re.compile(
        r'(\s+)with concurrent\.futures\.ThreadPoolExecutor\(max_workers=1\) as executor:\n\s+future = executor\.submit\((.*?)\)\n\s+response = future\.result\(timeout=60\)'
    )
    replacement1 = r'''\1executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
\1future = executor.submit(\2)
\1response = future.result(timeout=60)
\1executor.shutdown(wait=False)'''
    content = pattern1.sub(replacement1, content)
    
    # Fix max_workers=5 (process_chunk)
    pattern2 = re.compile(
        r'(\s+)with concurrent\.futures\.ThreadPoolExecutor\(max_workers=5\) as executor:\n\s+try:\n\s+for res in executor\.map\(process_chunk, chunk_data_list, timeout=180\):\n\s+extracted_text \+= res\n\s+except concurrent\.futures\.TimeoutError:\n\s+extracted_text \+= "\\n\[Speech Recognition Timeout: Part of the audio could not be processed\]\\n"\n\s+except Exception as e:\n\s+pass'
    )
    replacement2 = r'''\1executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
\1try:
\1    for res in executor.map(process_chunk, chunk_data_list, timeout=180):
\1        extracted_text += res
\1except concurrent.futures.TimeoutError:
\1    extracted_text += "\\n[Speech Recognition Timeout: Part of the audio could not be processed]\\n"
\1except Exception as e:
\1    pass
\1finally:
\1    executor.shutdown(wait=False)'''
    content = pattern2.sub(replacement2, content)
    
    # also replace any map that didn't get the timeout added correctly (audio_inograf or similar if there's any)
    pattern3 = re.compile(
        r'(\s+)with concurrent\.futures\.ThreadPoolExecutor\(max_workers=5\) as executor:\n\s+results = executor\.map\(process_chunk, chunk_data_list\)\n\s+for res in results:\n\s+extracted_text \+= res'
    )
    content = pattern3.sub(replacement2, content)
    
    return content

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = replace_with_block(content)
        
        if new_content != content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Fixed executor block in {fpath}')
