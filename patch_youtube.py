import os

base_dir = r'd:\Converter'
files = ['youtube_inograf/views.py', 'youtube_text/views.py']

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'import extract_youtube_transcript' not in content:
            # Add import
            content = content.replace('import os\n', 'import os\nfrom youtube_utils import extract_youtube_transcript\n')
            
            # Find the start of audio download
            old_start = '''        try:
            ydl_opts = {'''
            
            new_start = '''        try:
            extracted_text = extract_youtube_transcript(youtube_url, video_language)
            
            if not extracted_text:
                ydl_opts = {'''
                
            content = content.replace(old_start, new_start)
            
            # Now we need to indent everything from ydl_opts to the end of process_chunk map
            # This is tricky with replace. Let's do it line by line
            lines = content.split('\n')
            new_lines = []
            in_audio_block = False
            for line in lines:
                if 'ydl_opts = {' in line and 'if not extracted_text:' not in line:
                    in_audio_block = True
                
                if in_audio_block:
                    if line.startswith('            if not extracted_text.strip():'):
                        in_audio_block = False
                        
                if in_audio_block and line != '                ydl_opts = {':
                    if line.startswith('            '): # It's indented 12 spaces
                        new_lines.append('    ' + line) # Add 4 more spaces
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            content = '\n'.join(new_lines)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Patched {fpath}')
