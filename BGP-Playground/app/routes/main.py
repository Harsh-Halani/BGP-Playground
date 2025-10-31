"""
Main Routes Blueprint
Handles UI rendering endpoints
"""

from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Render main UI page"""
    return render_template('index.html')


@main_bp.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "BGP Playground"}, 200
