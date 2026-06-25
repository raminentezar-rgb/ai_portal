import re
import concurrent.futures

def _fetch_transcript(video_id, video_language):
    from youtube_transcript_api import YouTubeTranscriptApi
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    transcript = None
    
    # First try the exact requested language
    try:
        transcript = transcript_list.find_transcript([video_language, 'en', 'fa'])
    except:
        # Fallback to the first available transcript
        for t in transcript_list:
            transcript = t
            break
            
    if transcript:
        transcript_data = transcript.fetch()
        return " ".join([item['text'] for item in transcript_data])
    return None

def extract_youtube_transcript(url, video_language='fa'):
    try:
        video_id = None
        match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if match:
            video_id = match.group(1)
            
        if video_id:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(_fetch_transcript, video_id, video_language)
                return future.result(timeout=10) # 10 seconds timeout for fetching transcript
            except concurrent.futures.TimeoutError:
                pass
            except Exception as e:
                pass
            finally:
                executor.shutdown(wait=False)
    except Exception as e:
        pass
        
    return None
