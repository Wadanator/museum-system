#!/usr/bin/env python3
"""Utility functions for the Web Dashboard."""

import subprocess
from pathlib import Path
from werkzeug.utils import secure_filename
from ..config import Config

def get_scenes_path(controller):
    """Get the directory path for scene files (e.g., scenes/room1), ensuring it exists."""
    room_scenes_path = Path(getattr(controller, 'scenes_dir', Config.SCENES_DIR)) / getattr(controller, 'room_id', 'default')
    
    try:
        room_scenes_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        import logging
        logging.getLogger('WEB').error(f"Failed to create scenes directory {room_scenes_path}: {e}")
        
    return room_scenes_path

def get_scene_path(controller, scene_name):
    """Get the file path for a specific scene."""
    return get_scenes_path(controller) / secure_filename(scene_name)

def get_commands_path(controller):
    """Get the directory path for command files specific to the ROOM (e.g., scenes/room1/commands)."""
    room_path = get_scenes_path(controller)
    commands_path = room_path / 'commands'
    
    try:
        commands_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        import logging
        logging.getLogger('WEB').error(f"Failed to create commands directory {commands_path}: {e}")

    return commands_path

def get_command_path(controller, command_name):
    """Get the file path for a specific command, ensuring .json extension."""
    if not command_name.endswith('.json'):
        command_name += '.json'
    return get_commands_path(controller) / secure_filename(command_name)

def execute_system_command(command, operation, logger):
    """Execute a system command with error handling."""
    try:
        logger.info(f"{operation} requested via web dashboard")
        subprocess.run(command, check=True, capture_output=True, text=True)
        return {'success': True, 'message': f'{operation} initiated'}
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to {operation.lower()}: {e.stderr if e.stderr else 'Permission denied'}"
        logger.error(error_msg)
        return {'error': error_msg}
    except FileNotFoundError:
        error_msg = f"Command not found. Are you running on a Linux system?"
        logger.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f"Unexpected error during {operation.lower()}: {str(e)}"
        logger.error(error_msg)
        return {'error': error_msg}

def format_uptime(uptime_seconds):
    """Format uptime in seconds to human readable format."""
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"