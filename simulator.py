"""
BGP Playground - Complete BGP Simulator
Implements path-vector routing with BGP decision process
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from copy import deepcopy
import json


class OriginType(Enum):
    """BGP Origin Types"""
    IGP = 0  # Interior Gateway Protocol (best)
    EGP = 1  # Exterior Gateway Protocol
    INCOMPLETE = 2  # Unknown (worst)


class Route:
    """Represents a BGP route"""
    
    def __init__(self, prefix: str, as_path: List[str], 
                    origin: OriginType = OriginType.IGP,
                    local_pref: int = 100, med: int = 0,
                    next_hop: Optional[str] = None):
        self.prefix = prefix
        self.as_path = as_path.copy()
        self.origin = origin
        self.local_pref = local_pref
        self.med = med
        self.next_hop = next_hop
    
    def has_loop(self, asn: str) -> bool:
        """Check if ASN is in path (loop detection)"""
        return asn in self.as_path
    
    def clone(self) -> 'Route':
        """Create a deep copy of the route"""
        return Route(
            prefix=self.prefix,
            as_path=self.as_path.copy(),
            origin=self.origin,
            local_pref=self.local_pref,
            med=self.med,
            next_hop=self.next_hop
        )
    
    def to_dict(self) -> dict:
        """Convert route to dictionary"""
        return {
            "prefix": self.prefix,
            "as_path": self.as_path,
            "origin": self.origin.name,
            "local_pref": self.local_pref,
            "med": self.med,
            "next_hop": self.next_hop
        }


class Policy:
    """BGP routing policy"""
    
    def __init__(self, config: Optional[dict] = None):
        self.local_pref_map: Dict[str, int] = {}
        self.export_filters: List[Tuple[str, str]] = []
        self.as_path_prepend: int = 0
        
        if config:
            self.local_pref_map = config.get("local_pref", {})
            self.export_filters = config.get("export_filters", [])
            self.as_path_prepend = config.get("as_path_prepend", 0)
    
    def apply_import(self, route: Route, from_asn: str) -> Route:
        """Apply import policy to route"""
        modified = route.clone()
        
        # Apply LOCAL_PREF based on neighbor
        if from_asn in self.local_pref_map:
            modified.local_pref = self.local_pref_map[from_asn]
        
        return modified
    
    def apply_export(self, route: Route, to_asn: str) -> Optional[Route]:
        """Apply export policy to route. Returns None if filtered"""
        # Check export filters
        for action, prefix in self.export_filters:
            if action == "deny" and route.prefix == prefix:
                return None
        
        modified = route.clone()
        
        # AS_PATH prepending
        if self.as_path_prepend > 0:
            for _ in range(self.as_path_prepend):
                modified.as_path.insert(0, modified.as_path[0] if modified.as_path else to_asn)
        
        return modified


class ASNode:
    """Autonomous System node"""
    
    def __init__(self, asn: str, policy: Optional[Policy] = None):
        self.asn = asn
        self.neighbors: Set[str] = set()
        self.rib: Dict[str, Route] = {}  # Routing Information Base
        self.rib_in: Dict[str, Dict[str, Route]] = {}  # Per-neighbor RIB-In
        self.policy = policy or Policy()
    
    def add_neighbor(self, neighbor_asn: str):
        """Add BGP neighbor"""
        self.neighbors.add(neighbor_asn)
        self.rib_in[neighbor_asn] = {}
    
    def originate_route(self, prefix: str) -> Route:
        """Originate a new route for a prefix"""
        route = Route(
            prefix=prefix,
            as_path=[self.asn],
            origin=OriginType.IGP,
            local_pref=100
        )
        self.rib[prefix] = route
        return route
    
    def receive_route(self, route: Route, from_asn: str) -> bool:
        """
        Receive and process a BGP route.
        Returns True if route was accepted and caused a change.
        """
        # Loop prevention
        if route.has_loop(self.asn):
            return False
        
        # Apply import policy
        imported_route = self.policy.apply_import(route, from_asn)
        
        # Store in RIB-In
        self.rib_in[from_asn][route.prefix] = imported_route
        
        # Run decision process
        return self._run_decision_process(route.prefix)
    
    def withdraw_route(self, prefix: str, from_asn: str) -> bool:
        """
        Withdraw a route from a neighbor.
        Returns True if this caused a change in the best route.
        """
        if from_asn in self.rib_in and prefix in self.rib_in[from_asn]:
            del self.rib_in[from_asn][prefix]
            return self._run_decision_process(prefix)
        return False
    
    def _run_decision_process(self, prefix: str) -> bool:
        """
        Run BGP decision process for a prefix.
        Returns True if the best route changed.
        """
        # Collect all candidate routes
        candidates: List[Tuple[Route, str]] = []
        for neighbor, routes in self.rib_in.items():
            if prefix in routes:
                candidates.append((routes[prefix], neighbor))
        
        if not candidates:
            # No routes available, remove from RIB
            if prefix in self.rib:
                del self.rib[prefix]
                return True
            return False
        
        # Select best route using BGP decision process
        best_route = self._select_best_route(candidates)
        
        # Check if best route changed
        old_best = self.rib.get(prefix)
        if old_best and self._routes_equal(old_best, best_route):
            return False
        
        self.rib[prefix] = best_route
        return True
    
    def _select_best_route(self, candidates: List[Tuple[Route, str]]) -> Route:
        """
        BGP decision process:
        1. Highest LOCAL_PREF
        2. Shortest AS_PATH
        3. Lowest origin type (IGP < EGP < INCOMPLETE)
        4. Lowest MED
        5. Tie-breaker: first in list
        """
        if len(candidates) == 1:
            return candidates[0][0]
        
        # Sort by decision process criteria
        def compare_key(item):
            route, _ = item
            return (
                -route.local_pref,  # Higher is better (negate for sort)
                len(route.as_path),  # Shorter is better
                route.origin.value,  # Lower is better
                route.med  # Lower is better
            )
        
        candidates.sort(key=compare_key)
        return candidates[0][0]
    
    def _routes_equal(self, r1: Route, r2: Route) -> bool:
        """Check if two routes are equal"""
        return (r1.as_path == r2.as_path and 
                r1.local_pref == r2.local_pref and
                r1.origin == r2.origin)
    
    def get_routes_to_advertise(self) -> Dict[str, Route]:
        """Get routes to advertise to neighbors"""
        return self.rib.copy()
    
    def prepare_advertisement(self, route: Route, to_asn: str) -> Optional[Route]:
        """Prepare route for advertisement to neighbor"""
        # Apply export policy
        exported = self.policy.apply_export(route, to_asn)
        if not exported:
            return None
        
        # Prepend own ASN to path
        exported.as_path.insert(0, self.asn)
        exported.next_hop = self.asn
        
        return exported


class BGPSimulator:
    """Main BGP simulation engine"""
    
    def __init__(self, config: dict):
        self.config = config
        self.nodes: Dict[str, ASNode] = {}
        self.timeline: List[dict] = []
        self.current_step = 0
        self.max_steps = 100
        self.best_route_changes_total = 0
    
    def build_topology(self):
        """Build network topology from configuration"""
        # Create nodes with policies
        policies = self.config.get("policies", {})
        for node_asn in self.config["nodes"]:
            policy = Policy(policies.get(node_asn)) if node_asn in policies else Policy()
            self.nodes[node_asn] = ASNode(node_asn, policy)
        
        # Add links (bidirectional)
        for link in self.config["links"]:
            asn1, asn2 = link
            self.nodes[asn1].add_neighbor(asn2)
            self.nodes[asn2].add_neighbor(asn1)
    
    def log_event(self, event_type: str, **kwargs):
        """Log an event to timeline"""
        event = {
            "timestamp": self.current_step,
            "event_type": event_type,
            **kwargs
        }
        self.timeline.append(event)
    
    def run(self) -> dict:
        """Run the simulation"""
        self.build_topology()
        
        # Establish BGP sessions
        self._establish_sessions()
        
        # Execute scenario
        scenario = self.config.get("scenario", "baseline")
        if scenario == "baseline":
            self._run_baseline()
        elif scenario == "hijack":
            self._run_hijack()
        elif scenario == "route_flap":
            self._run_route_flap()
        
        # Generate results
        return self._generate_results()
    
    def _establish_sessions(self):
        """Establish BGP sessions between neighbors"""
        for asn, node in self.nodes.items():
            for neighbor in node.neighbors:
                self.log_event("open", from_as=asn, to_as=neighbor,
                             details="BGP session established")
    
    def _run_baseline(self):
        """Run baseline scenario - normal route propagation"""
        origin_asn = self.config["origin_as"]
        prefixes = self.config["prefixes"]
        
        # Origin announces prefixes
        for prefix in prefixes:
            route = self.nodes[origin_asn].originate_route(prefix)
            self.log_event("update", from_as=origin_asn, prefix=prefix,
                         details="Origin announcement")
        
        # Propagate until convergence
        self._propagate_until_convergence()
    
    def _run_hijack(self):
        """Run BGP hijack scenario"""
        origin_asn = self.config["origin_as"]
        hijacker_asn = self.config.get("hijacker")
        prefixes = self.config["prefixes"]
        
        if not hijacker_asn:
            return self._run_baseline()
        
        # Legitimate origin announces
        for prefix in prefixes:
            self.nodes[origin_asn].originate_route(prefix)
            self.log_event("update", from_as=origin_asn, prefix=prefix,
                         details="Legitimate origin announcement")
        
        self.current_step += 1
        self._propagate_until_convergence()
        
        # Hijacker announces same prefix
        for prefix in prefixes:
            route = self.nodes[hijacker_asn].originate_route(prefix)
            self.log_event("update", from_as=hijacker_asn, prefix=prefix,
                         details="HIJACK: Malicious announcement")
        
        self.current_step += 1
        self._propagate_until_convergence()
    
    def _run_route_flap(self):
        """Run route flap scenario"""
        origin_asn = self.config["origin_as"]
        prefixes = self.config["prefixes"]
        flap_count = self.config.get("flap_count", 3)
        
        for i in range(flap_count):
            # Announce
            for prefix in prefixes:
                self.nodes[origin_asn].originate_route(prefix)
                self.log_event("update", from_as=origin_asn, prefix=prefix,
                             details=f"Route announcement (flap {i+1})")
            
            self.current_step += 1
            self._propagate_until_convergence()
            
            # Withdraw
            for prefix in prefixes:
                if prefix in self.nodes[origin_asn].rib:
                    del self.nodes[origin_asn].rib[prefix]
                self.log_event("withdraw", from_as=origin_asn, prefix=prefix,
                             details=f"Route withdrawal (flap {i+1})")
            
            self.current_step += 1
            self._propagate_until_convergence()
    
    def _propagate_until_convergence(self):
        """Propagate routes until network converges"""
        converged = False
        iteration = 0
        
        while not converged and iteration < self.max_steps:
            converged = True
            self.current_step += 1
            iteration += 1
            
            # Each node advertises its best routes to neighbors
            for asn, node in self.nodes.items():
                routes_to_advertise = node.get_routes_to_advertise()
                
                for neighbor_asn in node.neighbors:
                    neighbor = self.nodes[neighbor_asn]
                    
                    for prefix, route in routes_to_advertise.items():
                        # Prepare advertisement
                        adv_route = node.prepare_advertisement(route, neighbor_asn)
                        
                        if adv_route:
                            # Send to neighbor
                            changed = neighbor.receive_route(adv_route, asn)
                            
                            if changed:
                                self.best_route_changes_total += 1
                                converged = False
                                self.log_event("update", from_as=asn, to_as=neighbor_asn,
                                             prefix=prefix, 
                                             details=f"Route update")
            
            # Send keepalives
            if converged:
                for asn, node in self.nodes.items():
                    for neighbor in node.neighbors:
                        self.log_event("keepalive", from_as=asn, to_as=neighbor)
    
    def _generate_results(self) -> dict:
        """Generate simulation results"""
        # Collect final RIBs
        final_ribs = {}
        for asn, node in self.nodes.items():
            final_ribs[asn] = {
                prefix: route.to_dict() 
                for prefix, route in node.rib.items()
            }
        
        # Calculate metrics
        metrics = self._calculate_metrics(final_ribs)
        
        # Generate topology representation
        topology = {
            "nodes": [{"id": asn} for asn in self.nodes.keys()],
            "edges": [
                {"from": link[0], "to": link[1]} 
                for link in self.config["links"]
            ]
        }
        
        return {
            "timeline": self.timeline,
            "metrics": metrics,
            "final_ribs": final_ribs,
            "topology": topology
        }
    
    def _calculate_metrics(self, final_ribs: dict) -> dict:
        """Calculate simulation metrics"""
        # Count event types
        event_counts = {}
        for event in self.timeline:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        metrics = {
            "convergence_steps": self.current_step,
            "total_updates": event_counts.get("update", 0),
            "total_events": len(self.timeline),
            "best_route_changes_total": self.best_route_changes_total
        }
        
        # Additional metrics
        # Average AS path length across all learned routes
        total_len = 0
        route_count = 0
        for rib in final_ribs.values():
            for route in rib.values():
                total_len += len(route["as_path"]) if "as_path" in route else 0
                route_count += 1
        metrics["avg_as_path_length"] = (total_len / route_count) if route_count > 0 else 0.0
        metrics["routes_learned_total"] = route_count
        
        # Reachable prefixes percent: fraction of (node,prefix) pairs that have a route
        prefixes = self.config.get("prefixes", [])
        if prefixes:
            total_pairs = len(self.nodes) * len(prefixes)
            reachable = 0
            for asn, rib in final_ribs.items():
                for p in prefixes:
                    if p in rib:
                        reachable += 1
            metrics["reachable_prefix_pairs_pct"] = (reachable / total_pairs * 100.0) if total_pairs > 0 else 0.0
        
        # Calculate hijack coverage if applicable
        if self.config.get("scenario") == "hijack":
            hijacker = self.config.get("hijacker")
            if hijacker:
                metrics["hijack_coverage_pct"] = self._calculate_hijack_coverage(
                    final_ribs, hijacker
                )
        
        return metrics
    
    def _calculate_hijack_coverage(self, ribs: dict, hijacker: str) -> float:
        """Calculate percentage of nodes routing through hijacker"""
        hijacked_count = 0
        total_count = 0
        
        for asn, rib in ribs.items():
            if asn == hijacker:
                continue
            
            for prefix, route in rib.items():
                total_count += 1
                if hijacker in route["as_path"]:
                    hijacked_count += 1
        
        return (hijacked_count / total_count * 100) if total_count > 0 else 0.0


def run_simulation(config: dict) -> dict:
    """
    Main entry point for running BGP simulation
    """
    simulator = BGPSimulator(config)
    return simulator.run()