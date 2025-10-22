"""
Unit tests for BGP Simulator
Tests core functionality: loop detection, decision process, policies
"""

import pytest
from simulator import Route, OriginType, ASNode, BGPSimulator, Policy, run_simulation


class TestRoute:
    """Route class tests"""
    
    def test_route_creation(self):
        """Test route object creation"""
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100", "200"],
            origin=OriginType.IGP
        )
        assert route.prefix == "10.0.1.0/24"
        assert route.as_path == ["100", "200"]
        assert route.origin == OriginType.IGP
    
    def test_loop_detection(self):
        """Test ASN loop detection in path"""
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100", "200", "300"]
        )
        
        assert route.has_loop("100") is True
        assert route.has_loop("200") is True
        assert route.has_loop("400") is False
    
    def test_route_clone(self):
        """Test route cloning"""
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100", "200"],
            local_pref=150
        )
        
        cloned = route.clone()
        cloned.as_path.append("300")
        
        # Original should be unchanged
        assert len(route.as_path) == 2
        assert len(cloned.as_path) == 3


class TestASNode:
    """ASNode class tests"""
    
    def test_node_creation(self):
        """Test AS node creation"""
        node = ASNode("100")
        assert node.asn == "100"
        assert len(node.neighbors) == 0
    
    def test_add_neighbor(self):
        """Test neighbor addition"""
        node = ASNode("100")
        node.add_neighbor("200")
        node.add_neighbor("300")
        
        assert "200" in node.neighbors
        assert "300" in node.neighbors
        assert len(node.neighbors) == 2
    
    def test_loop_prevention(self):
        """Test that routes with loops are rejected"""
        node = ASNode("100")
        node.add_neighbor("200")
        
        # Route with ASN 100 in path
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100", "200"]
        )
        
        result = node.receive_route(route, "200")
        assert result is False
        assert "10.0.1.0/24" not in node.rib
    
    def test_route_acceptance(self):
        """Test normal route acceptance"""
        node = ASNode("100")
        node.add_neighbor("200")
        
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["200", "300"]
        )
        
        result = node.receive_route(route, "200")
        assert result is True
        assert "10.0.1.0/24" in node.rib


class TestBGPDecisionProcess:
    """BGP decision process tests"""
    
    def test_local_pref_tiebreaker(self):
        """Test LOCAL_PREF is highest priority"""
        node = ASNode("100")
        node.add_neighbor("200")
        node.add_neighbor("300")
        
        # Route 1: higher LOCAL_PREF
        route1 = Route(
            prefix="10.0.1.0/24",
            as_path=["200", "400"],
            local_pref=150
        )
        
        # Route 2: lower LOCAL_PREF
        route2 = Route(
            prefix="10.0.1.0/24",
            as_path=["300"],
            local_pref=100
        )
        
        node.receive_route(route1, "200")
        node.receive_route(route2, "300")
        
        # Should prefer route1 due to higher LOCAL_PREF
        best = node.rib.get("10.0.1.0/24")
        assert best is not None
        assert best.local_pref == 150
    
    def test_as_path_length_tiebreaker(self):
        """Test AS_PATH length is second priority"""
        node = ASNode("100")
        node.add_neighbor("200")
        node.add_neighbor("300")
        
        # Route 1: longer path
        route1 = Route(
            prefix="10.0.1.0/24",
            as_path=["200", "300", "400"],
            local_pref=100
        )
        
        # Route 2: shorter path
        route2 = Route(
            prefix="10.0.1.0/24",
            as_path=["300"],
            local_pref=100
        )
        
        node.receive_route(route1, "200")
        node.receive_route(route2, "300")
        
        # Should prefer route2 due to shorter AS_PATH
        best = node.rib.get("10.0.1.0/24")
        assert best is not None
        assert len(best.as_path) == 1
    
    def test_origin_type_tiebreaker(self):
        """Test origin type tiebreaker"""
        node = ASNode("100")
        node.add_neighbor("200")
        node.add_neighbor("300")
        
        # Route 1: IGP origin (best)
        route1 = Route(
            prefix="10.0.1.0/24",
            as_path=["200"],
            local_pref=100,
            origin=OriginType.IGP
        )
        
        # Route 2: INCOMPLETE origin
        route2 = Route(
            prefix="10.0.1.0/24",
            as_path=["300"],
            local_pref=100,
            origin=OriginType.INCOMPLETE
        )
        
        node.receive_route(route1, "200")
        node.receive_route(route2, "300")
        
        best = node.rib.get("10.0.1.0/24")
        assert best.origin == OriginType.IGP
    
    def test_med_tiebreaker(self):
        """Test MED tiebreaker"""
        node = ASNode("100")
        node.add_neighbor("200")
        node.add_neighbor("300")
        
        # Route 1: higher MED
        route1 = Route(
            prefix="10.0.1.0/24",
            as_path=["200"],
            local_pref=100,
            origin=OriginType.IGP,
            med=100
        )
        
        # Route 2: lower MED
        route2 = Route(
            prefix="10.0.1.0/24",
            as_path=["300"],
            local_pref=100,
            origin=OriginType.IGP,
            med=50
        )
        
        node.receive_route(route1, "200")
        node.receive_route(route2, "300")
        
        best = node.rib.get("10.0.1.0/24")
        assert best.med == 50


class TestPolicy:
    """Policy application tests"""
    
    def test_import_policy_local_pref(self):
        """Test import policy sets LOCAL_PREF"""
        policy = Policy()
        policy.local_pref_map = {"200": 150, "300": 100}
        
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["200", "400"],
            local_pref=100
        )
        
        modified = policy.apply_import(route, "200")
        assert modified.local_pref == 150
        
        modified = policy.apply_import(route, "300")
        assert modified.local_pref == 100
    
    def test_export_policy_deny_filter(self):
        """Test export policy filters"""
        policy = Policy()
        policy.export_filters = [["deny", "10.0.1.0/24"]]
        
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100"]
        )
        
        result = policy.apply_export(route, "200")
        assert result is None  # Denied
    
    def test_export_policy_as_path_prepend(self):
        """Test AS_PATH prepending in export"""
        policy = Policy()
        policy.as_path_prepend = 2
        
        route = Route(
            prefix="10.0.1.0/24",
            as_path=["100", "200"]
        )
        
        result = policy.apply_export(route, "300")
        assert result is not None
        assert len(result.as_path) == 4  # 2 prepended + 2 original


class TestBGPSimulator:
    """BGP simulator integration tests"""
    
    def test_simple_three_as_line(self):
        """Test convergence in simple 3-AS line topology"""
        config = {
            "nodes": ["100", "200", "300"],
            "links": [["100", "200"], ["200", "300"]],
            "prefixes": ["10.0.1.0/24"],
            "origin_as": "100",
            "scenario": "baseline"
        }
        
        results = run_simulation(config)
        
        # Check convergence
        assert results["metrics"]["convergence_steps"] > 0
        assert results["metrics"]["total_updates"] > 0
        
        # All ASes should have the route
        assert "10.0.1.0/24" in results["final_ribs"]["100"]
        assert "10.0.1.0/24" in results["final_ribs"]["200"]
        assert "10.0.1.0/24" in results["final_ribs"]["300"]
        
        # Check AS paths are correct
        route_100 = results["final_ribs"]["100"]["10.0.1.0/24"]
        route_200 = results["final_ribs"]["200"]["10.0.1.0/24"]
        route_300 = results["final_ribs"]["300"]["10.0.1.0/24"]
        
        assert len(route_100["as_path"]) == 1  # Just 100
        assert "100" in route_200["as_path"]
        assert "100" in route_300["as_path"]
    
    def test_hijack_scenario(self):
        """Test BGP hijack scenario"""
        config = {
            "nodes": ["100", "200", "300"],
            "links": [["100", "200"], ["200", "300"]],
            "prefixes": ["10.0.1.0/24"],
            "origin_as": "100",
            "scenario": "hijack",
            "hijacker": "300"
        }
        
        results = run_simulation(config)
        
        # Hijacker should have the route
        assert "10.0.1.0/24" in results["final_ribs"]["300"]
        
        # Check hijack coverage metric
        assert "hijack_coverage_pct" in results["metrics"]
    
    def test_policy_local_pref(self):
        """Test LOCAL_PREF policy in simulation"""
        config = {
            "nodes": ["100", "200", "300"],
            "links": [["100", "200"], ["200", "300"], ["100", "300"]],
            "prefixes": ["10.0.1.0/24"],
            "origin_as": "100",
            "scenario": "baseline",
            "policies": {
                "300": {
                    "local_pref": {"100": 150, "200": 100}
                }
            }
        }
        
        results = run_simulation(config)
        
        # AS300 should prefer direct path from 100
        route_300 = results["final_ribs"]["300"]["10.0.1.0/24"]
        # Should have shorter AS path due to preference
        assert len(route_300["as_path"]) == 2  # [100, 300]
    
    def test_multiple_prefixes(self):
        """Test simulation with multiple prefixes"""
        config = {
            "nodes": ["100", "200", "300"],
            "links": [["100", "200"], ["200", "300"]],
            "prefixes": ["10.0.1.0/24", "10.0.2.0/24"],
            "origin_as": "100",
            "scenario": "baseline"
        }
        
        results = run_simulation(config)
        
        # Both prefixes should be in all RIBs
        assert "10.0.1.0/24" in results["final_ribs"]["300"]
        assert "10.0.2.0/24" in results["final_ribs"]["300"]


class TestEventTimeline:
    """Event timeline tests"""
    
    def test_timeline_has_events(self):
        """Test that timeline contains expected event types"""
        config = {
            "nodes": ["100", "200"],
            "links": [["100", "200"]],
            "prefixes": ["10.0.1.0/24"],
            "origin_as": "100",
            "scenario": "baseline"
        }
        
        results = run_simulation(config)
        
        event_types = set(e["event_type"] for e in results["timeline"])
        
        # Should have OPEN and UPDATE events
        assert "open" in event_types
        assert "update" in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])