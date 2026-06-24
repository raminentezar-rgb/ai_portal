import os
import re

base_dir = r'd:\Converter'
files = [
    'audio_inograf/views.py',
    'video_inograf/views.py',
    'youtube_inograf/views.py',
    'youtube_text/views.py',
    'video_text/views.py',
]

replacement = '''try:
                    for res in executor.map(process_chunk, chunk_data_list, timeout=180):
                        extracted_text += res
                except concurrent.futures.TimeoutError:
                    extracted_text += "\\n[Speech Recognition Timeout: Part of the audio could not be processed]\\n"
                except Exception as e:
                    pass'''

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Fix SyntaxWarning
        content = content.replace("'(youtube|youtu|youtube-nocookie)\\\\.(com|be)/'", "r'(youtube|youtu|youtube-nocookie)\\\\.(com|be)/'")
        content = content.replace("'(watch\\\\?v=|embed/|v/|.+\\\\?v=)?([^&=%\\\\?]{11})'", "r'(watch\\\\?v=|embed/|v/|.+\\\\?v=)?([^&=%\\\\?]{11})'")
        
        old_block = '''results = executor.map(process_chunk, chunk_data_list)
                for res in results:
                    extracted_text += res'''
                    
        new_content = content.replace(old_block, replacement)
        
        if new_content != content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Added timeout to executor.map in {fpath}')
