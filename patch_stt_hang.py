import os, glob

files = glob.glob('d:/Converter/**/*_inograf/views.py', recursive=True) + glob.glob('d:/Converter/**/*_text/views.py', recursive=True)

import socket
# We will inject socket timeout into the views where necessary!

for filepath in files:
    if 'Env' in filepath: continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'executor.map(process_chunk' in content:
        # Let's replace it with a submit loop!
        
        # We need to find the try-except-finally block exactly.
        import re
        
        pattern = r"(\s*)try:\s+for res in executor\.map\(process_chunk, chunk_data_list, timeout=180\):\s+extracted_text \+= res\s+except concurrent\.futures\.TimeoutError:\s+extracted_text \+= \"\\n\[Speech Recognition Timeout: Part of the audio could not be processed\]\\n\"\s+except Exception as e:\s+pass\s+finally:\s+executor\.shutdown\(wait=False\)"
        
        replacement = r"""\1try:
\1    import socket
\1    socket.setdefaulttimeout(30)
\1    futures = [executor.submit(process_chunk, chunk) for chunk in chunk_data_list]
\1    for future in futures:
\1        try:
\1            extracted_text += future.result(timeout=45)
\1        except concurrent.futures.TimeoutError:
\1            extracted_text += "\n[Speech Recognition Timeout: Audio chunk skipped]\n"
\1        except Exception as e:
\1            pass
\1except Exception as e:
\1    pass
\1finally:
\1    executor.shutdown(wait=False)"""

        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Patched {filepath}")
        else:
            print(f"Regex didn't match in {filepath}")
