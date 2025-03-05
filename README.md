# YouTube Video Data API

A Flask-based REST API that retrieves video data, transcripts, and subtitles from YouTube videos. This API provides easy access to video metadata and transcripts in multiple languages.

## Features

- Retrieve video metadata from YouTube URLs
- Extract video transcripts and subtitles
- Support for multiple languages
- Configurable response fields
- Swagger documentation interface
- Production-ready WSGI setup

## Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd yt-dl
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Development Setup

1. Install development dependencies:
```bash
pip install flask flasgger yt-dlp youtube-transcript-api requests
```

2. Run the development server:
```bash
python app.py
```

The development server will be available at `http://localhost:5000`

## Production Deployment

### Using Gunicorn (Recommended)

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
```

### Using Supervisor (Process Management)

1. Install Supervisor:
```bash
sudo apt-get install supervisor
```

2. Create Supervisor configuration:
```ini
# /etc/supervisor/conf.d/youtube_api.conf
[program:youtube_api]
directory=/path/to/your/app
command=gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
autostart=true
autorestart=true
stderr_logfile=/var/log/youtube_api.err.log
stdout_logfile=/var/log/youtube_api.out.log
```

3. Update Supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start youtube_api
```

### Using Nginx (Reverse Proxy)

1. Install Nginx:
```bash
sudo apt-get install nginx
```

2. Configure Nginx:
```nginx
# /etc/nginx/sites-available/youtube_api
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

3. Enable and start Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/youtube_api /etc/nginx/sites-enabled/
sudo nginx -t
sudo service nginx restart
```

## API Usage

### Endpoints

#### GET /video_data

Retrieves video data including title, metadata, and transcript.

**Parameters:**
- `video_url` (required): URL of the YouTube video
- `lang` (optional): Language code for subtitles (e.g., 'en', 'es', 'fr'). Default is 'en'
- `fields` (optional): Comma-separated list of fields to include (title, metadata, transcript)

**Example Requests:**

1. Basic request (all fields, English subtitles):
```bash
curl "http://localhost:5000/video_data?video_url=https://www.youtube.com/watch?v=VIDEO_ID"
```

2. Spanish subtitles:
```bash
curl "http://localhost:5000/video_data?video_url=https://www.youtube.com/watch?v=VIDEO_ID&lang=es"
```

3. Specific fields only:
```bash
curl "http://localhost:5000/video_data?video_url=https://www.youtube.com/watch?v=VIDEO_ID&fields=title,transcript"
```

**Example Response:**
```json
{
    "title": "Video Title",
    "transcript": {
        "segments": [
            {
                "text": "Transcript text segment",
                "start": 0.0,
                "duration": 2.5
            }
        ],
        "text": "Complete transcript text"
    }
}
```

## Swagger Documentation

Access the Swagger UI documentation at `http://your-domain/apidocs/` for interactive API documentation and testing.

## Error Handling

The API returns appropriate HTTP status codes:
- 200: Successful request
- 400: Missing required parameters
- 500: Internal server error

## Security Considerations

1. Always run behind a reverse proxy in production
2. Enable HTTPS
3. Implement rate limiting
4. Set up proper logging
5. Configure appropriate timeouts

## Monitoring and Logs

- Gunicorn access logs: `/var/log/gunicorn-access.log`
- Gunicorn error logs: `/var/log/gunicorn-error.log`
- Application logs: `/var/log/youtube_api.{err,out}.log`

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

[Your Support Information Here] 