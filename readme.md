# BGP Playground

A beautiful, interactive Flask web application for simulating BGP (Border Gateway Protocol) behavior with visualization, policy configuration, and comprehensive metrics.

## Overview

**BGP Playground** combines a Python BGP path-vector simulator with a modern web frontend to:

- 🌐 Simulate BGP announcements, route propagation, and convergence
- 🔒 Model BGP hijacks and route flapping scenarios
- 📊 Visualize AS topology and route state in real-time
- 📈 Measure convergence time, update churn, and RIB sizes
- 🎮 Support custom policies (LOCAL_PREF, AS_PATH prepending, export filters)
- 🚀 Provide reproducible experiments for computer networking coursework

## Quick Start

### Prerequisites

- Python 3.8+
- pip
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone or create the project directory:**
   ```bash
   mkdir bgp-playground
   cd bgp-playground
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python run.py
```

Open your browser and navigate to: **http://localhost:5000**

## Project Structure

```
bgp-playground/
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── app/
│   ├── __init__.py       # Application factory
│   ├── config.py         # Configuration settings
│   ├── models/           # Data models
│   │   ├── __init__.py
│   │   ├── as_node.py    # AS Node model
│   │   ├── policy.py     # Policy model
│   │   └── route.py      # Route model
│   ├── routes/           # API routes
│   │   ├── __init__.py
│   │   ├── api.py        # REST API endpoints
│   │   ├── examples.py   # Example scenarios
│   │   └── main.py       # Main routes
│   └── utils/            # Utilities
│       ├── __init__.py
│       ├── simulator.py  # BGP simulation engine
│       └── validators.py # Input validation
├── templates/
│   ├── base.html         # Base template with layout
│   └── index.html        # Main UI template
├── static/
│   ├── main.js           # Frontend logic & interactions
│   └── style.css         # Custom styles
├── tests/                # Unit tests
│   └── test_simulator.py
└── README.md            # This file
```

## Features

### 1. Interactive Web UI

- **Configuration Panel**: Load examples or paste custom JSON topology
- **Network Visualization**: Interactive AS topology graph using vis.js
- **Timeline View**: Step-by-step event log with message types
- **RIB Display**: Final routing tables for each AS
- **Metrics Dashboard**: Convergence time, update count, hijack coverage

### 2. BGP Simulator Core

**Implemented Concepts:**
- BGP path-vector routing algorithm
- BGP decision process (LOCAL_PREF → AS_PATH length → Origin → MED)
- Loop prevention (reject routes with own ASN)
- Export/import policies
- Multiple prefixes and RIBs
- Deterministic, step-based simulation

**Message Types:**
- OPEN: BGP session establishment
- KEEPALIVE: Session maintenance
- UPDATE: Route announcements
- WITHDRAW: Route withdrawals

**Scenario Types:**
- `baseline`: Normal convergence
- `hijack`: One AS announces another's prefix
- `route_flap`: Origin flaps route multiple times
- Custom scenarios via policy configuration

### 3. Policy Support

Configure per-AS policies:

```json
"policies": {
    "200": {
        "local_pref": {"100": 150, "300": 100},
        "export_filters": [["deny", "10.0.1.0/24"]],
        "as_path_prepend": 1
    }
}
```

### 4. Visualization & Analysis

- **Topology Graph**: Drag-and-drop nodes, color-coded by route availability
- **Event Timeline**: Playback control with step counter
- **Charts**: Event distribution over time, AS path length histogram
- **Export**: Download results as JSON for further analysis

## Usage Examples

### Example 1: Simple 3-AS Line Topology

```json
{
  "nodes": ["100", "200", "300"],
  "links": [["100", "200"], ["200", "300"]],
  "prefixes": ["10.0.1.0/24"],
  "origin_as": "100",
  "scenario": "baseline"
}
```

### Example 2: BGP Hijack Attack

AS300 hijacks the prefix announced by AS100:

```json
{
  "nodes": ["100", "200", "300", "400"],
  "links": [["100", "200"], ["200", "300"], ["200", "400"]],
  "prefixes": ["10.0.1.0/24"],
  "origin_as": "100",
  "scenario": "hijack",
  "hijacker": "300"
}
```

### Example 3: Policy-Based Routing

AS200 prefers paths through AS100:

```json
{
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
```

## API Reference

### POST /api/simulate

Run a BGP simulation.

**Request Body:**
```json
{
  "nodes": ["100", "200", "300"],
  "links": [["100", "200"], ["200", "300"]],
  "prefixes": ["10.0.1.0/24"],
  "origin_as": "100",
  "scenario": "baseline",
  "hijacker": "300",
  "policies": { ... }
}
```

**Response:**
```json
{
  "timeline": [
    {
      "timestamp": 0,
      "event_type": "open",
      "from_as": "100",
      "to_as": "200",
      "details": "BGP session established"
    },
    ...
  ],
  "metrics": {
    "convergence_steps": 5,
    "total_updates": 14,
    "total_events": 32,
    "hijack_coverage_pct": 75.0
  },
  "final_ribs": {
    "100": { "10.0.1.0/24": { ... } },
    "200": { "10.0.1.0/24": { ... } },
    ...
  },
  "topology": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### GET /api/examples

Get all built-in example topologies.

### GET /api/status

Health check endpoint.

## Simulator Internals

### BGP Decision Process (Implemented)

Routes are selected in this order:

1. **Highest LOCAL_PREF** - Administrative preference
2. **Shortest AS_PATH** - Fewest hops in AS path
3. **Origin Type** - IGP < EGP < INCOMPLETE
4. **Lowest MED** - Multi-Exit Discriminator
5. **Tie-breaker** - First route in list (stable)

### Classes

- **`Route`**: Represents a BGP route with prefix, AS path, origin, metrics
- **`ASNode`**: Autonomous System with RIB-In/RIB-Out and policies
- **`Policy`**: Per-AS import/export policy configuration
- **`BGPSimulator`**: Main simulation engine with event queue and timeline

### Execution Model

1. Topology is built from nodes and links
2. Origin AS announces prefix(es)
3. Updates propagate synchronously through event queue
4. Each node runs BGP decision process on receipt
5. Changed routes are re-advertised to neighbors
6. Simulation continues until convergence or max steps
7. Timeline, metrics, and final RIB state are returned

## Testing

Run unit tests:

```bash
pytest
```

Add tests in a `test_simulator.py` file to verify:
- Loop detection
- Decision process tiebreakers
- Policy application
- Route convergence

## Extending the Project

### Phase 1: Advanced Features

- [ ] RPKI origin validation model
- [ ] AS path hijacking detection
- [ ] Real-time topology editing
- [ ] Scenario replay and step-through

### Phase 2: Real-World Integration

- [ ] Docker/containerlab integration for real FRR routers
- [ ] ExaBGP controlled announcements
- [ ] tcpdump packet capture comparison
- [ ] RPKI validator (Routinator) integration

### Phase 3: Analysis Tools

- [ ] Jupyter notebooks for batch experiments
- [ ] Convergence time vs. topology size plots
- [ ] Update churn analysis
- [ ] Policy effectiveness studies

## Educational Value

This project demonstrates:

- **Routing Protocols**: BGP path-vector algorithm, decision process
- **Control Plane**: Route propagation, loop prevention
- **Security**: BGP hijacks, RPKI validation (extension)
- **Performance**: Convergence metrics, update churn
- **Software Architecture**: Layered design (simulator → API → UI)

## Troubleshooting

### Port Already in Use

Change the port in `app/config.py`:
```python
PORT = 5001  # Change to desired port
```

### JSON Parse Error

Ensure your topology JSON is valid. Use an online JSON validator or copy from examples.

### Simulation Hangs

Check for infinite loops in topology. All nodes should be connected or in separate components.

## Performance

- Small topologies (< 10 nodes): < 100ms
- Medium topologies (10-50 nodes): < 500ms
- Large topologies (50+ nodes): Depends on scenario complexity

For production use, consider caching or background job queues.

## License

Educational use. Modify and distribute freely.

## References

- RFC 4271: Border Gateway Protocol
- RFC 6811: BGP Resource Public Key Infrastructure
- "Computer Networking" by Kurose & Ross
- FRR (Free Range Routing) documentation
- ExaBGP simulator documentation

## Author

Created as a Computer Networking course project.
By - Hrushi Bhanvadiya and Harsh Halani

---

**Questions or issues?** Check the example scenarios first, then verify your JSON configuration matches the API specification.
