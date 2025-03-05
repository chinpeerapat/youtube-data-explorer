from flask import Flask, request, jsonify
from flasgger import Swagger
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import requests

app = Flask(__name__)
swagger = Swagger(app)

def get_video_metadata(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info

def get_transcript(video_id, lang='en'):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        # Combine all transcript segments into a single text
        transcript_text = ' '.join([entry['text'] for entry in transcript])
        return {
            'segments': transcript,
            'text': transcript_text
        }
    except Exception:
        return None

def get_fallback_subtitle(metadata, lang='en'):
    # Try to retrieve subtitles from both 'subtitles' and 'automatic_captions'
    for key in ['subtitles', 'automatic_captions']:
        captions = metadata.get(key, {})
        if lang in captions and captions[lang]:
            subtitle_url = captions[lang][0].get('url')
            if subtitle_url:
                try:
                    response = requests.get(subtitle_url)
                    if response.status_code == 200:
                        # You might want to add proper parsing of the subtitle format here
                        return {
                            'raw': response.text,
                            'text': response.text  # Add proper parsing as needed
                        }
                except Exception:
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
        description: Language code for subtitles (e.g., 'en', 'es', 'fr'). Default is 'en'.
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
            transcript:
              type: object
              properties:
                segments:
                  type: array
                  items:
                    type: object
                text:
                  type: string
      400:
        description: Missing required parameter.
      500:
        description: Internal server error.
    """
    video_url = request.args.get('video_url')
    if not video_url:
        return jsonify({'error': 'Missing "video_url" parameter'}), 400

    # Get language parameter
    lang = request.args.get('lang', 'en')

    # Parse the fields parameter; default returns all fields.
    fields_param = request.args.get('fields')
    if fields_param:
        fields = set(f.strip().lower() for f in fields_param.split(',') if f.strip())
    else:
        fields = {"title", "metadata", "transcript"}

    result = {}
    metadata = None

    # Only call get_video_metadata if any requested field needs it.
    if fields.intersection({"title", "metadata", "transcript"}):
        try:
            metadata = get_video_metadata(video_url)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    if "title" in fields:
        result["title"] = metadata.get("title") if metadata else None

    if "metadata" in fields:
        result["metadata"] = metadata

    if "transcript" in fields:
        video_id = metadata.get("id") if metadata else None
        transcript = None
        if video_id:
            transcript = get_transcript(video_id, lang)
            if transcript is None:
                transcript = get_fallback_subtitle(metadata, lang)
        result["transcript"] = transcript

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)