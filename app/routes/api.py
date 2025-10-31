"""
API Routes Blueprint
Handles REST API endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from app.utils import run_simulation, validate_config
from app.utils.validators import ValidationError
from app.routes.examples import get_examples

api_bp = Blueprint('api', __name__)


@api_bp.route('/status', methods=['GET'])
def status():
    """
    Health check endpoint
    
    Returns:
        JSON response with service status
    """
    return jsonify({
        "status": "ok",
        "service": "BGP Playground",
        "version": "1.0.0"
    })


@api_bp.route('/simulate', methods=['POST'])
def simulate():
    """
    Run BGP simulation
    
    Expected JSON body:
    {
        "nodes": ["100", "200", "300"],
        "links": [["100", "200"], ["200", "300"]],
        "prefixes": ["10.0.1.0/24"],
        "origin_as": "100",
        "scenario": "baseline|hijack|route_flap",
        "hijacker": "300",  // for hijack scenario
        "policies": {
            "200": {
                "local_pref": {"100": 100, "300": 50},
                "export_filters": [["deny", "10.0.1.0/24"]],
                "as_path_prepend": 1
            }
        }
    }
    
    Returns:
        JSON response with simulation results
    """
    try:
        config = request.get_json()
        
        if not config:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate configuration
        try:
            validated_config = validate_config(config)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        
        # Run simulation
        current_app.logger.info(f"Running simulation with config: {validated_config}")
        results = run_simulation(validated_config)
        
        current_app.logger.info(f"Simulation completed successfully")
        return jsonify(results)
    
    except ValidationError as e:
        current_app.logger.warning(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        current_app.logger.error(f"Simulation error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500


@api_bp.route('/examples', methods=['GET'])
def examples():
    """
    Get example topologies
    
    Returns:
        JSON response with example configurations
    """
    try:
        examples_data = get_examples()
        return jsonify(examples_data)
    except Exception as e:
        current_app.logger.error(f"Error loading examples: {str(e)}")
        return jsonify({"error": "Failed to load examples"}), 500


@api_bp.route('/validate', methods=['POST'])
def validate():
    """
    Validate configuration without running simulation
    
    Returns:
        JSON response indicating if configuration is valid
    """
    try:
        config = request.get_json()
        
        if not config:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate configuration
        try:
            validated_config = validate_config(config)
            return jsonify({
                "valid": True,
                "message": "Configuration is valid",
                "config": validated_config
            })
        except ValidationError as e:
            return jsonify({
                "valid": False,
                "error": str(e)
            }), 400
    
    except Exception as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 500
