from functools import wraps
from flask import session, redirect, jsonify, request


def login_required(f):
    """Allow any logged-in user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Allow only admin users."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        if session.get('user_role') != 'admin':
            if request.is_json:
                return jsonify({'error': 'Forbidden'}), 403
            return redirect('/billing')
        return f(*args, **kwargs)
    return wrapper
