"""
BGP Policy Model
Implements import and export policies
"""

from typing import Dict, List, Optional, Tuple
from app.models.route import Route


class Policy:
    """BGP routing policy"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        Initialize policy from configuration
        
        Args:
            config: Dictionary with policy configuration
        """
        self.local_pref_map: Dict[str, int] = {}
        self.export_filters: List[Tuple[str, str]] = []
        self.as_path_prepend: int = 0
        
        if config:
            self.local_pref_map = config.get("local_pref", {})
            self.export_filters = config.get("export_filters", [])
            self.as_path_prepend = config.get("as_path_prepend", 0)
    
    def apply_import(self, route: Route, from_asn: str) -> Route:
        """
        Apply import policy to route
        
        Args:
            route: Route to apply policy to
            from_asn: AS number of neighbor sending route
            
        Returns:
            Modified route with import policy applied
        """
        modified = route.clone()
        
        # Apply LOCAL_PREF based on neighbor
        if from_asn in self.local_pref_map:
            modified.local_pref = self.local_pref_map[from_asn]
        
        return modified
    
    def apply_export(self, route: Route, to_asn: str) -> Optional[Route]:
        """
        Apply export policy to route
        
        Args:
            route: Route to apply policy to
            to_asn: AS number of neighbor receiving route
            
        Returns:
            Modified route with export policy applied, or None if filtered
        """
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
    
    def __repr__(self) -> str:
        """String representation of policy"""
        return f"Policy(local_pref={self.local_pref_map}, filters={len(self.export_filters)}, prepend={self.as_path_prepend})"
