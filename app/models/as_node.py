"""
Autonomous System Node Model
Represents an AS in the BGP network
"""

from typing import Dict, List, Optional, Set, Tuple
from app.models.route import Route
from app.models.policy import Policy


class ASNode:
    """Autonomous System node"""
    
    def __init__(self, asn: str, policy: Optional[Policy] = None):
        """
        Initialize AS node
        
        Args:
            asn: AS number
            policy: BGP policy (optional)
        """
        self.asn = asn
        self.neighbors: Set[str] = set()
        self.rib: Dict[str, Route] = {}  # Routing Information Base
        self.rib_in: Dict[str, Dict[str, Route]] = {}  # Per-neighbor RIB-In
        self.policy = policy or Policy()
        print(f"Initialized AS{asn} node")
    
    def add_neighbor(self, neighbor_asn: str):
        """
        Add BGP neighbor
        
        Args:
            neighbor_asn: AS number of neighbor
        """
        self.neighbors.add(neighbor_asn)
        self.rib_in[neighbor_asn] = {}
    
    def originate_route(self, prefix: str) -> Route:
        """
        Originate a new route for a prefix
        
        Args:
            prefix: IP prefix to originate
            
        Returns:
            Originated route
        """
        from app.models.route import OriginType
        
        route = Route(
            prefix=prefix,
            as_path=[self.asn],
            origin=OriginType.IGP,
            local_pref=100,
            next_hop=self.asn
        )
        print(f"AS{self.asn} originating route for {prefix}")
        
        # Store in RIB-In from self
        if self.asn not in self.rib_in:
            self.rib_in[self.asn] = {}
        self.rib_in[self.asn][prefix] = route
        
        # Store in RIB and trigger decision process
        self.rib[prefix] = route
        self._run_decision_process(prefix)
        print(f"AS{self.asn} RIB after origination: {self.rib}")
        return route
    
    def receive_route(self, route: Route, from_asn: str) -> bool:
        """
        Receive and process a BGP route
        
        Args:
            route: Route received
            from_asn: AS number of sender
            
        Returns:
            True if route was accepted and caused a change
        """
        print(f"AS{self.asn} receiving route from AS{from_asn} for prefix {route.prefix}")
        
        # Loop prevention
        if route.has_loop(self.asn):
            print(f"AS{self.asn} detected loop in path {route.as_path}")
            return False
        
        # Validate next_hop attribute
        if not route.next_hop:
            print(f"AS{self.asn} received route with no next_hop")
            return False
            
        # Apply import policy
        imported_route = self.policy.apply_import(route, from_asn)
        if not imported_route:
            print(f"AS{self.asn} route filtered by import policy")
            return False
        
        # Create a new copy for modification
        imported_route = imported_route.clone()
        
        # Store in RIB-In with validated next_hop
        if from_asn not in self.rib_in:
            self.rib_in[from_asn] = {}
        
        imported_route.next_hop = from_asn
        self.rib_in[from_asn][route.prefix] = imported_route
        
        print(f"AS{self.asn} stored route in RIB-IN from AS{from_asn}")
        
        # Run decision process
        changed = self._run_decision_process(route.prefix)
        print(f"AS{self.asn} decision process result: changed={changed}")
        print(f"AS{self.asn} current RIB: {self.rib}")
        return changed
    
    def withdraw_route(self, prefix: str, from_asn: str) -> bool:
        """
        Withdraw a route from a neighbor
        
        Args:
            prefix: Prefix to withdraw
            from_asn: AS number of sender
            
        Returns:
            True if this caused a change in the best route
        """
        if from_asn in self.rib_in and prefix in self.rib_in[from_asn]:
            del self.rib_in[from_asn][prefix]
            return self._run_decision_process(prefix)
        return False
    
    def _run_decision_process(self, prefix: str) -> bool:
        """
        Run BGP decision process for a prefix
        
        Args:
            prefix: Prefix to run decision process for
            
        Returns:
            True if the best route changed
        """
        print(f"AS{self.asn} running decision process for prefix {prefix}")
        
        # Collect all candidate routes
        candidates: List[Tuple[Route, str]] = []
        for neighbor, routes in self.rib_in.items():
            if prefix in routes:
                route = routes[prefix]
                candidates.append((route, neighbor))
                print(f"Candidate from AS{neighbor}: {route.as_path}")
        
        if not candidates:
            print(f"AS{self.asn} no candidates available for {prefix}")
            # No routes available, remove from RIB
            if prefix in self.rib:
                del self.rib[prefix]
                print(f"AS{self.asn} removed route for {prefix} from RIB")
                return True
            return False
        
        # Select best route using BGP decision process
        best_route = self._select_best_route(candidates)
        print(f"AS{self.asn} selected best route: {best_route.as_path}")
        
        # Check if best route changed
        old_best = self.rib.get(prefix)
        if old_best and self._routes_equal(old_best, best_route):
            print(f"AS{self.asn} best route unchanged")
            return False
        
        # Store new best route
        self.rib[prefix] = best_route.clone()
        print(f"AS{self.asn} updated RIB with new best route for {prefix}")
        return True
    
    def _select_best_route(self, candidates: List[Tuple[Route, str]]) -> Route:
        """
        BGP decision process
        
        Args:
            candidates: List of (route, neighbor) tuples
            
        Returns:
            Best route selected
        """
        if len(candidates) == 1:
            return candidates[0][0]
        
        # Group routes by next hop AS to compare MEDs correctly
        routes_by_first_as = {}
        for route, neighbor in candidates:
            first_as = route.as_path[0] if route.as_path else neighbor
            if first_as not in routes_by_first_as:
                routes_by_first_as[first_as] = []
            routes_by_first_as[first_as].append((route, neighbor))
        
        # For each next hop AS, select best route considering MED
        best_per_as = []
        for routes in routes_by_first_as.values():
            routes.sort(key=lambda x: (x[0].med, x[1]))
            best_per_as.append(routes[0])
        
        # Final comparison across different next hop ASes
        def compare_key(item):
            route, neighbor = item
            return (
                -route.local_pref,
                len(route.as_path),
                route.origin.value,
                neighbor
            )
        
        best_per_as.sort(key=compare_key)
        return best_per_as[0][0]
    
    def _routes_equal(self, r1: Route, r2: Route) -> bool:
        """
        Check if two routes are equal
        
        Args:
            r1: First route
            r2: Second route
            
        Returns:
            True if routes are equal
        """
        return (r1.as_path == r2.as_path and 
                r1.local_pref == r2.local_pref and
                r1.origin == r2.origin)
    
    def get_routes_to_advertise(self) -> Dict[str, Route]:
        """
        Get routes to advertise to neighbors
        
        Returns:
            Dictionary of prefix -> route
        """
        return self.rib.copy()
    
    def prepare_advertisement(self, route: Route, to_asn: str) -> Optional[Route]:
        """
        Prepare route for advertisement to neighbor
        
        Args:
            route: Route to advertise
            to_asn: AS number of recipient
            
        Returns:
            Prepared route, or None if filtered
        """
        print(f"AS{self.asn} preparing advertisement to AS{to_asn} for prefix {route.prefix}")
        
        # Don't advertise routes learned from this neighbor (split horizon)
        if route.next_hop == to_asn:
            print(f"Skipping route learned from AS{to_asn}")
            return None
            
        # Apply export policy
        exported = self.policy.apply_export(route, to_asn)
        if not exported:
            print(f"Route filtered by export policy")
            return None
        
        # Create a new copy for modification
        exported = exported.clone()
        
        # Prepend own ASN to path if not already there
        if not exported.as_path or exported.as_path[0] != self.asn:
            exported.as_path.insert(0, self.asn)
        exported.next_hop = self.asn
        
        print(f"Prepared route: prefix={exported.prefix}, as_path={exported.as_path}, next_hop={exported.next_hop}")
        return exported
    
    def __repr__(self) -> str:
        """String representation of AS node"""
        return f"ASNode(AS{self.asn}, neighbors={len(self.neighbors)}, routes={len(self.rib)})"
