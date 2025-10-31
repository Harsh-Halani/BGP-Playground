"""
BGP Route Model
Represents a BGP route with all attributes
"""

from enum import Enum
from typing import List, Optional


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
        """
        Initialize a BGP route
        
        Args:
            prefix: IP prefix (e.g., "10.0.1.0/24")
            as_path: List of AS numbers in path
            origin: Origin type (IGP, EGP, or INCOMPLETE)
            local_pref: Local preference value
            med: Multi-Exit Discriminator value
            next_hop: Next hop AS number
        """
        self.prefix = prefix
        self.as_path = as_path.copy()
        self.origin = origin
        self.local_pref = local_pref
        self.med = med
        self.next_hop = next_hop
    
    def has_loop(self, asn: str) -> bool:
        """
        Check if ASN is in path (loop detection)
        
        Args:
            asn: AS number to check
            
        Returns:
            True if ASN is in path, False otherwise
        """
        return asn in self.as_path
    
    def clone(self) -> 'Route':
        """
        Create a deep copy of the route
        
        Returns:
            Cloned Route object
        """
        return Route(
            prefix=self.prefix,
            as_path=self.as_path.copy(),
            origin=self.origin,
            local_pref=self.local_pref,
            med=self.med,
            next_hop=self.next_hop
        )
    
    def to_dict(self) -> dict:
        """
        Convert route to dictionary representation
        
        Returns:
            Dictionary with route attributes
        """
        return {
            "prefix": self.prefix,
            "as_path": self.as_path,
            "origin": self.origin.name,
            "local_pref": self.local_pref,
            "med": self.med,
            "next_hop": self.next_hop
        }
    
    def __repr__(self) -> str:
        """String representation of route"""
        return f"Route({self.prefix}, path={self.as_path}, lp={self.local_pref})"
