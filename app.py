"""
BGP Playground - Flask Application
Main web server with REST API and UI endpoints
"""

from flask import Flask, render_template, request, jsonify
from simulator import run_simulation
import json

app = Flask(__name__)


@app.route('/')
def index():
    """Render main UI"""
    return render_template('index.html')


@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "BGP Playground",
        "version": "1.0.0"
    })


@app.route('/api/simulate', methods=['POST'])
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
    """
    try:
        config = request.get_json()
        
        # Validate required fields
        if not config.get("nodes"):
            return jsonify({"error": "Missing 'nodes' field"}), 400
        
        if not config.get("links"):
            return jsonify({"error": "Missing 'links' field"}), 400
        
        # Set defaults
        if "prefixes" not in config:
            config["prefixes"] = ["10.0.1.0/24"]
        
        if "origin_as" not in config:
            config["origin_as"] = config["nodes"][0]
        
        if "scenario" not in config:
            config["scenario"] = "baseline"
        
        # Run simulation
        results = run_simulation(config)
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/examples', methods=['GET'])
def examples():
    """Get example topologies"""
    examples = {
        "simple_line": {
            "name": "Simple Line Topology",
            "description": "Three ASes in a line",
            "config": {
                "nodes": ["100", "200", "300"],
                "links": [["100", "200"], ["200", "300"]],
                "prefixes": ["10.0.1.0/24"],
                "origin_as": "100",
                "scenario": "baseline"
            }
        },
        "hijack_scenario": {
            "name": "BGP Hijack Attack",
            "description": "AS300 hijacks AS100's prefix",
            "config": {
                "nodes": ["100", "200", "300", "400"],
                "links": [["100", "200"], ["200", "300"], ["200", "400"]],
                "prefixes": ["10.0.1.0/24"],
                "origin_as": "100",
                "scenario": "hijack",
                "hijacker": "300"
            }
        },
        "policy_preference": {
            "name": "Local Preference Policy",
            "description": "AS200 prefers AS100 over AS300",
            "config": {
                "nodes": ["100", "200", "300"],
                "links": [["100", "200"], ["200", "300"], ["100", "300"]],
                "prefixes": ["10.0.1.0/24"],
                "origin_as": "100",
                "scenario": "baseline",
                "policies": {
                    "200": {
                        "local_pref": {"100": 150, "300": 100}
                    }
                }
            }
        },
        "route_flap": {
            "name": "Route Flap Damping Test",
            "description": "Origin flaps the route multiple times",
            "config": {
                "nodes": ["100", "200", "300", "400"],
                "links": [["100", "200"], ["200", "300"], ["300", "400"]],
                "prefixes": ["10.0.1.0/24"],
                "origin_as": "100",
                "scenario": "route_flap",
                "flap_count": 3
            }
        },
        "mesh_topology": {
            "name": "Full Mesh",
            "description": "Four ASes fully connected",
            "config": {
                "nodes": ["100", "200", "300", "400"],
                "links": [
                    ["100", "200"], ["100", "300"], ["100", "400"],
                    ["200", "300"], ["200", "400"], ["300", "400"]
                ],
                "prefixes": ["10.0.1.0/24"],
                "origin_as": "100",
                "scenario": "baseline"
            }
        },
        "med_tie_break": {
            "name": "MED Tie-Break",
            "description": "Two paths with equal LOCAL_PREF and AS_PATH, lower MED wins",
            "config": {
                "nodes": ["100", "200", "300"],
                "links": [["100", "200"], ["100", "300"], ["200", "300"]],
                "prefixes": ["10.0.2.0/24"],
                "origin_as": "200",
                "scenario": "baseline",
                "policies": {
                    "300": {"local_pref": {"100": 100, "200": 100}}
                }
            }
        },
        "as_path_prepend": {
            "name": "AS Path Prepend",
            "description": "AS200 prepends to de-prefer one path",
            "config": {
                "nodes": ["100", "200", "300"],
                "links": [["100", "200"], ["200", "300"], ["100", "300"]],
                "prefixes": ["10.0.3.0/24"],
                "origin_as": "100",
                "scenario": "baseline",
                "policies": {
                    "200": {"as_path_prepend": 2}
                }
            }
        },
        "export_filtering": {
            "name": "Selective Export",
            "description": "AS200 denies exporting a specific prefix",
            "config": {
                "nodes": ["100", "200", "300"],
                "links": [["100", "200"], ["200", "300"]],
                "prefixes": ["10.0.4.0/24", "10.0.5.0/24"],
                "origin_as": "100",
                "scenario": "baseline",
                "policies": {
                    "200": {"export_filters": [["deny", "10.0.4.0/24"]]}
                }
            }
        },
        "star_topology": {
            "name": "Star Topology",
            "description": "AS200 as a hub with four spokes",
            "config": {
                "nodes": ["100", "200", "300", "400", "500"],
                "links": [["200", "100"], ["200", "300"], ["200", "400"], ["200", "500"]],
                "prefixes": ["10.0.6.0/24"],
                "origin_as": "100",
                "scenario": "baseline"
            }
        },
        "ring_topology": {
            "name": "Ring Topology",
            "description": "Five ASes in a ring",
            "config": {
                "nodes": ["100", "200", "300", "400", "500"],
                "links": [["100", "200"], ["200", "300"], ["300", "400"], ["400", "500"], ["500", "100"]],
                "prefixes": ["10.0.7.0/24"],
                "origin_as": "100",
                "scenario": "baseline"
            }
        },
        "multi_prefix": {
            "name": "Multiple Prefixes",
            "description": "Origin announces multiple prefixes",
            "config": {
                "nodes": ["100", "200", "300", "400"],
                "links": [["100", "200"], ["200", "300"], ["300", "400"], ["100", "400"]],
                "prefixes": ["10.0.8.0/24", "10.0.9.0/24", "10.0.10.0/24"],
                "origin_as": "100",
                "scenario": "baseline"
            }
        }
    }
    
    return jsonify(examples)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)