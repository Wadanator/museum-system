#!/usr/bin/env python3
"""Authentication helpers for the Web Dashboard."""

from functools import wraps
from flask import request, Response
from .config import Config

def check_auth(username, password):
    """Validate provided username and password against configured credentials."""
    return username == Config.USERNAME and password == Config.PASSWORD

def authenticate():
    """Return a 401 response to trigger basic authentication prompt."""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    """Decorator to enforce basic authentication on routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated