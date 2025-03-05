from flask import Flask, request, jsonify
from flasgger import Swagger
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import requests

app = Flask(__name__)
swagger = Swagger(app)

def get_video_metadata(url, browser='chrome'):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'cookiesfrombrowser': (browser,),  # Use specified browser's cookies
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # Return only essential metadata
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'duration': info.get('duration'),
            'view_count': info.get('view_count'),
            'channel': info.get('channel'),
            'upload_date': info.get('upload_date'),
            'description': info.get('description'),
            'subtitles': info.get('subtitles', {}),
            'automatic_captions': info.get('automatic_captions', {})
        }

def get_transcript(video_id, lang='en'):
    try:
        # First try to get transcript in the exact language
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            # Ensure we have the correct structure with timing information
            segments = [{
                'text': entry['text'],
                'start': entry['start'],
                'duration': entry['duration']
            } for entry in transcript]
            return {
                'segments': segments,
                'text': ' '.join([entry['text'] for entry in transcript])
            }
        except Exception as e:
            print(f"Direct transcript failed: {str(e)}")
            # If exact language not found, try to get transcript with translation
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                translated = transcript_list.translate(lang).fetch()
                segments = [{
                    'text': entry['text'],
                    'start': entry['start'],
                    'duration': entry['duration']
                } for entry in translated]
                return {
                    'segments': segments,
                    'text': ' '.join([entry['text'] for entry in translated])
                }
            except Exception as e:
                print(f"Translation failed: {str(e)}")
                return None
    except Exception as e:
        print(f"Error getting transcript: {str(e)}")
        return None

def get_fallback_subtitle(metadata, lang='en'):
    # Try to retrieve subtitles from both 'subtitles' and 'automatic_captions'
    for key in ['subtitles', 'automatic_captions']:
        captions = metadata.get(key, {})
        # Check for exact language match first
        if lang in captions:
            subtitle_formats = captions[lang]
            # Try to get vtt format first, then json3, then srv1, then others
            format_preference = ['vtt', 'json3', 'srv1']
            chosen_format = None
            
            # First try preferred formats
            for fmt in format_preference:
                chosen_format = next((f for f in subtitle_formats if f.get('ext') == fmt), None)
                if chosen_format:
                    break
            
            # If no preferred format found, take the first available
            if not chosen_format and subtitle_formats:
                chosen_format = subtitle_formats[0]
            
            if chosen_format and chosen_format.get('url'):
                try:
                    response = requests.get(chosen_format['url'])
                    if response.status_code == 200:
                        content = response.text
                        
                        # Handle different subtitle formats
                        if chosen_format.get('ext') == 'json3':
                            # Parse JSON3 format
                            import json
                            try:
                                json_data = json.loads(content)
                                events = json_data.get('events', [])
                                segments = []
                                full_text = []
                                for event in events:
                                    if 'segs' in event:
                                        text = ' '.join(seg.get('utf8', '') for seg in event['segs'] if 'utf8' in seg)
                                        if text.strip():
                                            segments.append({
                                                'text': text,
                                                'start': event.get('tStartMs', 0) / 1000,
                                                'duration': (event.get('dDurationMs', 0) / 1000)
                                            })
                                            full_text.append(text)
                                return {
                                    'segments': segments,
                                    'text': ' '.join(full_text)
                                }
                            except json.JSONDecodeError:
                                pass
                        
                        else:  # VTT or other text formats
                            lines = content.split('\n')
                            segments = []
                            current_time = None
                            current_text = []
                            
                            for line in lines:
                                line = line.strip()
                                if not line or line == 'WEBVTT' or line.isdigit():
                                    continue
                                    
                                # Try to parse timestamp
                                if '-->' in line:
                                    if current_time and current_text:
                                        segments.append({
                                            'text': ' '.join(current_text),
                                            'start': current_time,
                                            'duration': 0  # We don't parse duration for simplicity
                                        })
                                    try:
                                        timestamp = line.split('-->')[0].strip()
                                        # Convert timestamp to seconds
                                        parts = timestamp.replace(',', '.').split(':')
                                        current_time = float(parts[-1]) + float(parts[-2]) * 60
                                        if len(parts) > 2:
                                            current_time += float(parts[-3]) * 3600
                                        current_text = []
                                    except:
                                        continue
                                elif current_time is not None:
                                    # This is subtitle text
                                    if line:
                                        current_text.append(line)
                            
                            # Add the last segment
                            if current_time and current_text:
                                segments.append({
                                    'text': ' '.join(current_text),
                                    'start': current_time,
                                    'duration': 0
                                })
                            
                            if segments:
                                return {
                                    'segments': segments,
                                    'text': ' '.join(seg['text'] for seg in segments)
                                }
                                
                except Exception as e:
                    print(f"Error parsing subtitles: {str(e)}")
                    continue
    return None

@app.route('/video_data', methods=['GET'])
def video_data():
    """
    Retrieve YouTube video data.
    This endpoint returns video title, metadata, and transcript by default,
    but you can limit the fields by using the "fields" query parameter.
    ---
    parameters:
      - name: video_url
        in: query
        type: string
        required: true
        description: URL of the YouTube video.
      - name: fields
        in: query
        type: string
        required: false
        description: Comma-separated list of fields to include (title, metadata, transcript). Default returns all.
      - name: lang
        in: query
        type: string
        required: false
        description: ISO 639-1 language code for subtitles (e.g., 'en', 'es', 'fr'). Default is 'en'. Will attempt to translate if direct subtitles not available.
      - name: browser
        in: query
        type: string
        required: false
        description: Browser to extract cookies from (chrome, firefox, opera, edge, safari). Default is 'chrome'.
    responses:
      200:
        description: A JSON object containing the requested video data.
        schema:
          type: object
          properties:
            title:
              type: string
            metadata:
              type: object
              properties:
                id:
                  type: string
                title:
                  type: string
                duration:
                  type: integer
                view_count:
                  type: integer
                channel:
                  type: string
                upload_date:
                  type: string
                description:
                  type: string
            transcript:
              type: object
              properties:
                segments:
                  type: array
                  items:
                    type: object
                    properties:
                      text:
                        type: string
                      start:
                        type: number
                      duration:
                        type: number
                text:
                  type: string
                source:
                  type: string
                  description: Source of the transcript (direct, translated, or fallback)
      400:
        description: Missing required parameter or invalid language code.
      500:
        description: Internal server error.
    """
    video_url = request.args.get('video_url')
    if not video_url:
        return jsonify({'error': 'Missing "video_url" parameter'}), 400

    # Get parameters
    lang = request.args.get('lang', 'en').lower()
    browser = request.args.get('browser', 'chrome')

    # Validate language code (basic validation)
    if not lang.isalpha() or len(lang) != 2:
        return jsonify({'error': 'Invalid language code. Please use ISO 639-1 format (e.g., "en", "es", "fr")'}), 400

    # Validate browser parameter
    valid_browsers = {'chrome', 'firefox', 'opera', 'edge', 'safari'}
    if browser.lower() not in valid_browsers:
        return jsonify({'error': f'Invalid browser. Must be one of: {", ".join(valid_browsers)}'}), 400

    # Parse the fields parameter; default returns all fields.
    fields_param = request.args.get('fields')
    if fields_param:
        fields = set(f.strip().lower() for f in fields_param.split(',') if f.strip())
    else:
        fields = {"title", "metadata", "transcript"}

    try:
        metadata = get_video_metadata(video_url, browser.lower()) if fields.intersection({"title", "metadata", "transcript"}) else None
        result = {}

        if "title" in fields:
            result["title"] = metadata.get("title") if metadata else None

        if "metadata" in fields:
            # Remove subtitle data from metadata to keep response clean
            metadata_clean = metadata.copy() if metadata else {}
            metadata_clean.pop('subtitles', None)
            metadata_clean.pop('automatic_captions', None)
            result["metadata"] = metadata_clean

        if "transcript" in fields and metadata:
            video_id = metadata.get("id")
            transcript = None
            if video_id:
                # Try getting transcript through API first
                transcript = get_transcript(video_id, lang)
                if transcript:
                    transcript['source'] = 'direct' if lang in (metadata.get('subtitles') or {}) else 'translated'
                else:
                    # Fallback to subtitle parsing
                    transcript = get_fallback_subtitle(metadata, lang)
                    if transcript:
                        transcript['source'] = 'fallback'
            
            result["transcript"] = transcript

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        # Try port 8000 first, fallback to other ports if needed
        ports = [8000, 8080, 5000]
        for port in ports:
            try:
                app.run(host='0.0.0.0', port=port, debug=True)
                break
            except OSError as e:
                if port == ports[-1]:  # If this is the last port to try
                    print(f"Could not bind to any of the ports: {ports}")
                    raise e
                print(f"Port {port} is in use, trying next port...")
                continue
    except Exception as e:
        print(f"Error starting the server: {e}")