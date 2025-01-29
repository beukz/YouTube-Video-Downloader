from flask import Flask, request, jsonify, render_template
import os
import subprocess
from pytubefix import YouTube
from pytubefix.cli import on_progress
import yt_dlp
 
app = Flask(__name__)

# Route to render the index.html
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_media', methods=['POST'])
def fetch_media():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        # Step 1: Download the video using yt-dlp
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Best video and audio available
            'outtmpl': 'downloads/%(title)s.%(ext)s',  # Output template
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',  # Ensure to convert to a suitable format
                'preferedformat': 'mp4',
            }],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)

        # Step 2: Download audio using pytubefix
        yt = YouTube(url, on_progress_callback=on_progress)
        audio_stream = yt.streams.get_audio_only()  # Get audio stream
        audio_file = f'downloads/{yt.title}.mp3'
        audio_stream.download(filename=audio_file)

        # Step 3: Merge video and audio using FFmpeg
        merged_file = f'downloads/{yt.title}_merged.mp4'
        merge_command = [
            'ffmpeg', '-i', video_file, '-i', audio_file,
            '-c:v', 'copy', '-c:a', 'aac', merged_file
        ]
        subprocess.run(merge_command, check=True)

        # Clean up the individual files if necessary
        os.remove(video_file)
        os.remove(audio_file)

        return jsonify({"video_url": merged_file}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure the downloads directory exists
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    app.run(debug=True)
