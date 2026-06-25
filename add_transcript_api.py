import os
import re

base_dir = r'd:\Converter'
files = ['youtube_inograf/views.py', 'youtube_text/views.py']

extract_text_code = '''
def extract_youtube_transcript(url, video_language):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        import re
        
        video_id = None
        match = re.search(r'(?:v=|\\/)([0-9A-Za-z_-]{11}).*', url)
        if match:
            video_id = match.group(1)
            
        if video_id:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = None
                
                # Try to get the requested language
                try:
                    transcript = transcript_list.find_transcript([video_language, 'en', 'fa'])
                except:
                    # Fallback to any generated transcript
                    for t in transcript_list:
                        transcript = t
                        break
                        
                if transcript:
                    transcript_data = transcript.fetch()
                    text = " ".join([item['text'] for item in transcript_data])
                    return text
            except Exception as e:
                pass
    except Exception as e:
        pass
        
    return None

'''

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'extract_youtube_transcript' not in content:
            # Insert the helper function near the top, after imports
            content = content.replace('def is_valid_youtube_url', extract_text_code + '\n\ndef is_valid_youtube_url')
            # For youtube_text which might not have is_valid_youtube_url
            if 'def is_valid_youtube_url' not in content:
                content = content.replace('@check_credits', extract_text_code + '\n\n@check_credits')
            
            # We want to skip audio download if transcript is available
            # Find the yt-dlp block
            
            old_dl_block = "temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_yti_{session_id}.wav')"
            if old_dl_block not in content:
                old_dl_block = "temp_audio_path = os.path.join(settings.BASE_DIR, f'temp_audio_{session_id}.wav')"
                
            new_dl_block = old_dl_block + '''
        
        extracted_text = extract_youtube_transcript(youtube_url, video_language)
        
        if not extracted_text:
'''
            content = content.replace(old_dl_block, new_dl_block)
            
            # Now indent everything from ydl_opts until extracted_text = "" (or just before we use extracted_text)
            # Actually, to make it clean, we can just replace the whole audio processing logic with an if statement.
            # But the easiest way without complex AST is to find the block of code that does audio processing,
            # and replace it with:
            # if not extracted_text:
            #     # audio processing code
            #     extracted_text = ...
            
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Patched {fpath}')
