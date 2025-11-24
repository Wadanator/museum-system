#!/usr/bin/env python3
"""Main routes for serving the React Web Dashboard."""

import os
from flask import Blueprint, send_from_directory

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(BASE_DIR, 'dist')

# Blueprint staticky ukazuje na 'dist'
main_bp = Blueprint('main', __name__, static_folder=DIST_DIR)

@main_bp.route('/', defaults={'path': ''})
@main_bp.route('/<path:path>')
def serve(path):
    """
    Obsluhuje React aplikáciu (SPA Routing).
    """

    if path != "" and os.path.exists(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)
    

    return send_from_directory(DIST_DIR, 'index.html')