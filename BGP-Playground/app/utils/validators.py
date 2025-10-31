"""
Configuration Validators
Validation functions for simulation configurations
"""

from typing import Dict, List, Any
from flask import current_app


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_config(config: dict) -> Dict[str, Any]:
    """
    Validate simulation configuration
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Validated and normalized configuration
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if not isinstance(config, dict):
        raise ValidationError("Configuration must be a dictionary")
    
    # Validate required fields
    if "nodes" not in config:
        raise ValidationError("Missing required field: 'nodes'")
    
    if "links" not in config:
        raise ValidationError("Missing required field: 'links'")
    
    # Validate nodes
    nodes = config["nodes"]
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValidationError("'nodes' must be a non-empty list")
    
    # Check max nodes limit
    max_nodes = current_app.config.get('MAX_NODES', 100)
    if len(nodes) > max_nodes:
        raise ValidationError(f"Too many nodes (max: {max_nodes})")
    
    # Validate all nodes are strings
    for node in nodes:
        if not isinstance(node, str):
            raise ValidationError(f"Node {node} must be a string")
    
    # Validate links
    links = config["links"]
    if not isinstance(links, list):
        raise ValidationError("'links' must be a list")
    
    for link in links:
        if not isinstance(link, list) or len(link) != 2:
            raise ValidationError(f"Link {link} must be a list of 2 elements")
        
        # Check that both nodes exist
        if link[0] not in nodes or link[1] not in nodes:
            raise ValidationError(f"Link {link} references non-existent node")
    
    # Validate prefixes
    prefixes = config.get("prefixes", ["10.0.1.0/24"])
    if not isinstance(prefixes, list):
        raise ValidationError("'prefixes' must be a list")
    
    # Check max prefixes limit
    max_prefixes = current_app.config.get('MAX_PREFIXES', 50)
    if len(prefixes) > max_prefixes:
        raise ValidationError(f"Too many prefixes (max: {max_prefixes})")
    
    for prefix in prefixes:
        if not isinstance(prefix, str):
            raise ValidationError(f"Prefix {prefix} must be a string")
        if not _is_valid_prefix(prefix):
            raise ValidationError(f"Invalid prefix format: {prefix}")
    
    config["prefixes"] = prefixes
    
    # Validate origin_as
    origin_as = config.get("origin_as", nodes[0])
    if origin_as not in nodes:
        raise ValidationError(f"origin_as '{origin_as}' not in nodes list")
    config["origin_as"] = origin_as
    
    # Validate scenario
    scenario = config.get("scenario", "baseline")
    valid_scenarios = ["baseline", "hijack", "route_flap"]
    if scenario not in valid_scenarios:
        raise ValidationError(f"Invalid scenario. Must be one of: {valid_scenarios}")
    config["scenario"] = scenario
    
    # Validate hijacker for hijack scenario
    if scenario == "hijack":
        hijacker = config.get("hijacker")
        if not hijacker:
            raise ValidationError("'hijacker' field required for hijack scenario")
        if hijacker not in nodes:
            raise ValidationError(f"hijacker '{hijacker}' not in nodes list")
    
    # Validate policies
    policies = config.get("policies", {})
    if not isinstance(policies, dict):
        raise ValidationError("'policies' must be a dictionary")
    
    for asn, policy in policies.items():
        if asn not in nodes:
            raise ValidationError(f"Policy for AS '{asn}' references non-existent node")
        
        if not isinstance(policy, dict):
            raise ValidationError(f"Policy for AS '{asn}' must be a dictionary")
        
        # Validate local_pref
        if "local_pref" in policy:
            local_pref = policy["local_pref"]
            if not isinstance(local_pref, dict):
                raise ValidationError(f"local_pref for AS '{asn}' must be a dictionary")
            
            for neighbor, pref in local_pref.items():
                if neighbor not in nodes:
                    raise ValidationError(f"local_pref references non-existent neighbor '{neighbor}'")
                if not isinstance(pref, int) or pref < 0:
                    raise ValidationError(f"local_pref value must be a non-negative integer")
        
        # Validate export_filters
        if "export_filters" in policy:
            filters = policy["export_filters"]
            if not isinstance(filters, list):
                raise ValidationError(f"export_filters for AS '{asn}' must be a list")
            
            for filter_rule in filters:
                if not isinstance(filter_rule, list) or len(filter_rule) != 2:
                    raise ValidationError(f"export_filter rule must be [action, prefix]")
                
                action, prefix = filter_rule
                if action not in ["deny", "permit"]:
                    raise ValidationError(f"filter action must be 'deny' or 'permit'")
                if not isinstance(prefix, str):
                    raise ValidationError(f"filter prefix must be a string")
        
        # Validate as_path_prepend
        if "as_path_prepend" in policy:
            prepend = policy["as_path_prepend"]
            if not isinstance(prepend, int) or prepend < 0 or prepend > 10:
                raise ValidationError(f"as_path_prepend must be an integer between 0 and 10")
    
    # Validate flap_count for route_flap scenario
    if scenario == "route_flap":
        flap_count = config.get("flap_count", 3)
        if not isinstance(flap_count, int) or flap_count < 1 or flap_count > 10:
            raise ValidationError("flap_count must be an integer between 1 and 10")
        config["flap_count"] = flap_count
    
    return config


def _is_valid_prefix(prefix: str) -> bool:
    """
    Validate IP prefix format
    
    Args:
        prefix: IP prefix string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if '/' not in prefix:
            return False
        
        ip_part, mask_part = prefix.split('/')
        
        # Validate mask
        mask = int(mask_part)
        if mask < 0 or mask > 32:
            return False
        
        # Validate IP address
        octets = ip_part.split('.')
        if len(octets) != 4:
            return False
        
        for octet in octets:
            num = int(octet)
            if num < 0 or num > 255:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False
