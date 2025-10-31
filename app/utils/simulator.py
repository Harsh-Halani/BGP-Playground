"""
BGP Simulator Utilities
Main simulation engine and helpers
"""

from typing import Dict, List
from app.models import Route, ASNode, Policy


class BGPSimulator:
    """Main BGP simulation engine"""
    
    def __init__(self, config: dict):
        """
        Initialize simulator
        
        Args:
            config: Simulation configuration dictionary
        """
        self.config = config
        self.nodes: Dict[str, ASNode] = {}
        self.timeline: List[dict] = []
        self.current_step = 0
        self.max_steps = config.get('max_steps', 100)
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
        """
        Log an event to timeline
        
        Args:
            event_type: Type of event
            **kwargs: Event attributes
        """
        event = {
            "timestamp": self.current_step,
            "event_type": event_type,
            **kwargs
        }
        self.timeline.append(event)
    
    def run(self) -> dict:
        """
        Run the simulation
        
        Returns:
            Dictionary with simulation results
        """
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
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
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
        
        print(f"\nStarting baseline scenario with origin AS{origin_asn}")
        print(f"Prefixes to announce: {prefixes}")
        
        # Origin announces prefixes
        for prefix in prefixes:
            print(f"\nOrigin AS{origin_asn} announcing prefix {prefix}")
            route = self.nodes[origin_asn].originate_route(prefix)
            self.log_event("update", from_as=origin_asn, prefix=prefix,
                         details="Origin announcement")
        
        # Propagate until convergence
        print("\nStarting route propagation")
        self._propagate_until_convergence()
        
        # Verify final routing tables
        print("\nFinal Routing Tables:")
        for asn, node in self.nodes.items():
            print(f"\nAS{asn} RIB:")
            for prefix, route in node.rib.items():
                print(f"  {prefix}: AS_PATH={route.as_path}, next_hop={route.next_hop}")
    
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
            
            # Keep track of updates to process in this iteration
            updates_to_process = []
            
            # Each node advertises its best routes to neighbors
            for asn, node in self.nodes.items():
                routes_to_advertise = node.get_routes_to_advertise()
                
                for neighbor_asn in node.neighbors:
                    neighbor = self.nodes[neighbor_asn]
                    
                    for prefix, route in routes_to_advertise.items():
                        # Prepare advertisement
                        adv_route = node.prepare_advertisement(route, neighbor_asn)
                        
                        if adv_route:
                            updates_to_process.append((asn, neighbor_asn, prefix, adv_route))
            
            # Process all queued updates
            for update in updates_to_process:
                from_asn, to_asn, prefix, adv_route = update
                neighbor = self.nodes[to_asn]
                
                # Send to neighbor
                changed = neighbor.receive_route(adv_route, from_asn)
                
                if changed:
                    self.best_route_changes_total += 1
                    converged = False
                    self.log_event("update", from_as=from_asn, to_as=to_asn,
                                 prefix=prefix, 
                                 details=f"Route update")
            
            # Send keepalives only if no updates were processed
            if not updates_to_process:
                for asn, node in self.nodes.items():
                    for neighbor in node.neighbors:
                        self.log_event("keepalive", from_as=asn, to_as=neighbor)
    
    def _generate_results(self) -> dict:
        """
        Generate simulation results
        
        Returns:
            Dictionary with results
        """
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
        """
        Calculate simulation metrics
        
        Args:
            final_ribs: Final routing tables
            
        Returns:
            Dictionary with metrics
        """
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
        
        # Average AS path length
        total_len = 0
        route_count = 0
        for rib in final_ribs.values():
            for route in rib.values():
                total_len += len(route["as_path"]) if "as_path" in route else 0
                route_count += 1
        metrics["avg_as_path_length"] = (total_len / route_count) if route_count > 0 else 0.0
        metrics["routes_learned_total"] = route_count
        
        # Reachable prefixes percent
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
        """
        Calculate percentage of nodes routing through hijacker
        
        Args:
            ribs: Final routing tables
            hijacker: Hijacker AS number
            
        Returns:
            Percentage of hijacked routes
        """
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
    
    Args:
        config: Simulation configuration
        
    Returns:
        Simulation results
    """
    simulator = BGPSimulator(config)
    return simulator.run()
