import re

def extract_youtube_transcript(url, video_language='fa'):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        video_id = None
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if match:
            video_id = match.group(1)
            
        if video_id:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                transcript = None
                
                # First try the exact requested language
                try:
                    transcript = transcript_list.find_transcript([video_language, 'en', 'fa'])
                except:
                    # Fallback to the first available transcript (auto-generated or manual)
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
