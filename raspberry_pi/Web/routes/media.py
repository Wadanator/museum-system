#!/usr/bin/env python3
import os
import logging
from flask import Blueprint, jsonify, request, send_from_directory, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import time
import configparser
from ..auth import requires_auth

# Inicializácia Blueprintu
media_bp = Blueprint('media', __name__)
logger = logging.getLogger('museum.web.media')

# Povolené prípony
ALLOWED_EXTENSIONS = {
    'video': {'mp4', 'avi', 'mov', 'mkv', 'png', 'jpg', 'jpeg'},
    'audio': {'mp3', 'wav', 'ogg', 'flac'}
}

def get_media_path(media_type):
    """
    Načíta cestu priamo z config.ini súboru.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir)) # raspberry_pi/
    config_path = os.path.join(root_dir, 'config', 'config.ini')
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    room_id = config.get('Room', 'room_id', fallback='room1')
    scenes_dir = config.get('Scenes', 'directory', fallback='scenes')
    
    if media_type == 'video':
        media_dir_name = config.get('Video', 'directory', fallback='videos')
    else:
        media_dir_name = config.get('Audio', 'directory', fallback='audio')

    full_path = os.path.join(root_dir, scenes_dir, room_id, media_dir_name)
    return Path(full_path)

def allowed_file(filename, media_type):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(media_type, set())

def get_file_info(file_path):
    try:
        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        modified_time = time.strftime('%d.%m.%Y %H:%M', time.localtime(stat.st_mtime))
        
        return {
            'name': file_path.name,
            'size': f"{size_mb:.1f} MB",
            'modified': modified_time
        }
    except Exception as e:
        return {'name': file_path.name, 'size': '?', 'modified': '?'}

@media_bp.route('/<media_type>', methods=['GET'])
@requires_auth
def list_files(media_type):
    """Vráti zoznam súborov."""
    if media_type not in ['video', 'audio']:
        return jsonify({'error': 'Invalid media type'}), 400

    try:
        folder_path = get_media_path(media_type)
        
        if not folder_path.exists():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
            except:
                pass
            return jsonify([]), 200

        files = []
        for f in folder_path.iterdir():
            if f.is_file() and allowed_file(f.name, media_type):
                files.append(get_file_info(f))
        
        return jsonify(files), 200
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return jsonify({'error': str(e)}), 500

@media_bp.route('/<media_type>', methods=['POST'])
@requires_auth
def upload_file(media_type):
    """Nahrá súbor."""
    if media_type not in ['video', 'audio']:
        return jsonify({'error': 'Invalid media type'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename, media_type):
        try:
            filename = secure_filename(file.filename)
            folder_path = get_media_path(media_type)
            folder_path.mkdir(parents=True, exist_ok=True)
            
            file_path = folder_path / filename
            file.save(str(file_path))
            
            logger.info(f"File uploaded: {file_path}")
            return jsonify({'message': 'OK', 'file': get_file_info(file_path)}), 201
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'File type not allowed'}), 400

@media_bp.route('/<media_type>/<filename>', methods=['DELETE'])
@requires_auth
def delete_file(media_type, filename):
    """Vymaže súbor."""
    try:
        folder_path = get_media_path(media_type)
        file_path = folder_path / secure_filename(filename)
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {file_path}")
            return jsonify({'message': 'Deleted'}), 200
        return jsonify({'error': 'Not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@media_bp.route('/play/audio', methods=['POST'])
@requires_auth
def play_audio():
    """Okamžite prehrá vybraný audio súbor."""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'Filename missing'}), 400

        # Získame controller z kontextu aplikácie
        controller = current_app.config.get('CONTROLLER')
        
        if controller and controller.audio_handler:
            success = controller.audio_handler.play_audio(filename)
            if success:
                return jsonify({'status': 'playing', 'file': filename})
            else:
                return jsonify({'error': 'Failed to play audio (check logs)'}), 500
        else:
            return jsonify({'error': 'Audio Handler not initialized'}), 500

    except Exception as e:
        logger.error(f"Play Audio Error: {e}")
        return jsonify({'error': str(e)}), 500

@media_bp.route('/play/video', methods=['POST'])
@requires_auth
def play_video():
    """Okamžite prehrá vybraný video súbor."""
    try:
        data = request.json
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'Filename missing'}), 400

        controller = current_app.config.get('CONTROLLER')
        
        if controller and controller.video_handler:
            success = controller.video_handler.play_video(filename)
            if success:
                return jsonify({'status': 'playing', 'file': filename})
            else:
                return jsonify({'error': 'Failed to play video'}), 500
        else:
            return jsonify({'error': 'Video Handler not initialized'}), 500

    except Exception as e:
        logger.error(f"Play Video Error: {e}")
        return jsonify({'error': str(e)}), 500

@media_bp.route('/stop', methods=['POST'])
@requires_auth
def stop_all_media():
    """Zastaví všetko Audio aj Video (Panic Button)."""
    try:
        controller = current_app.config.get('CONTROLLER')
        if not controller:
             return jsonify({'error': 'Controller unavailable'}), 500
        
        stopped = []
        if controller.audio_handler:
            controller.audio_handler.stop_audio()
            stopped.append('audio')
            
        if controller.video_handler:
            controller.video_handler.stop_video()
            stopped.append('video')
            
        return jsonify({'status': 'stopped', 'components': stopped})

    except Exception as e:
        logger.error(f"Stop Media Error: {e}")
        return jsonify({'error': str(e)}), 500