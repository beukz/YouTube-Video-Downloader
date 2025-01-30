from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from urllib.parse import quote, unquote
import os
import yt_dlp
import time
import threading
import json
import logging
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

progress_data = {}

class ProgressHook:
    def __init__(self, task_id):
        self.task_id = task_id

    def hook(self, d):
        try:
            if d['status'] == 'downloading':
                # Clean ANSI escape codes and percentage
                percent_str = d.get('_percent_str', '0%')
                clean_percent = re.sub(r'[^\d.]', '', percent_str).strip('%') or '0'
                
                progress_data[self.task_id] = {
                    'progress': float(clean_percent),
                    'status': 'Downloading',
                    'filename': d.get('filename', '')
                }
            elif d['status'] == 'postprocessing':
                progress_data[self.task_id] = {
                    'progress': 100,
                    'status': 'Merging video & audio',
                    'filename': d.get('info_dict', {}).get('_filename', '')
                }
        except Exception as e:
            app.logger.error(f"Progress hook error: {str(e)}")

def cleanup_downloads():
    while True:
        time.sleep(3600)
        now = time.time()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > 3600:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        app.logger.error(f"Error deleting {file_path}: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_media', methods=['POST'])
def fetch_media():
    data = request.get_json()
    url = data.get('url')
    task_id = str(time.time())

    if not url or 'youtube.com/' not in url and 'youtu.be/' not in url:
        return jsonify({"error": "Please enter a valid YouTube URL"}), 400

    try:
        progress_data[task_id] = {'progress': 0, 'status': 'Starting...'}
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': 'mp4'
            }],
            'progress_hooks': [ProgressHook(task_id).hook],
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info)
            
            # Ensure MP4 extension
            final_filename = os.path.splitext(base_filename)[0] + '.mp4'
            
            # Sanitize filename
            sanitized_name = secure_filename(os.path.basename(final_filename))
            sanitized_path = os.path.join(DOWNLOAD_FOLDER, sanitized_name)
            
            # Rename if different from original
            if final_filename != sanitized_path:
                if os.path.exists(final_filename):
                    os.rename(final_filename, sanitized_path)
                else:
                    final_filename = sanitized_path

            # Verify file exists
            if not os.path.exists(sanitized_path):
                raise Exception(f"File {sanitized_name} not found on server")

        # URL-encode the sanitized filename
        encoded_name = quote(sanitized_name)
        
        progress_data[task_id]['status'] = 'Complete'
        progress_data[task_id]['progress'] = 100
        
        return jsonify({
            "video_url": f"/downloads/{encoded_name}",
            "preview_url": f"/preview/{encoded_name}",
            "task_id": task_id
        }), 200

    except yt_dlp.utils.DownloadError as e:
        error_msg = "YouTube error: " + str(e).split('\n')[0]
        app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        app.logger.error(f"General error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route('/progress/<task_id>')
def progress(task_id):
    def generate():
        while True:
            data = progress_data.get(task_id, {})
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/downloads/<path:filename>')
def serve_download(filename):
    decoded_name = unquote(filename)
    return send_from_directory(DOWNLOAD_FOLDER, decoded_name, as_attachment=True)

@app.route('/preview/<path:filename>')
def preview_file(filename):
    decoded_name = unquote(filename)
    return send_from_directory(DOWNLOAD_FOLDER, decoded_name)

if __name__ == '__main__':
    cleanup_thread = threading.Thread(target=cleanup_downloads, daemon=True)
    cleanup_thread.start()
    app.run(debug=True)