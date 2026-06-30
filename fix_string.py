import glob, os

files = glob.glob('d:/Converter/**/*_inograf/views.py', recursive=True) + glob.glob('d:/Converter/**/*_text/views.py', recursive=True)

old_str = 'extracted_text += "\n[Speech Recognition Timeout: Audio chunk skipped]\n"'
new_str = 'extracted_text += "\\n[Speech Recognition Timeout: Audio chunk skipped]\\n"'

for filepath in files:
    if 'Env' in filepath: continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if old_str in content:
        new_content = content.replace(old_str, new_str)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print('Fixed', filepath)
