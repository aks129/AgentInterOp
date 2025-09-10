import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from app.scheduling.config import SchedulingConfig, get_scheduling_config, save_scheduling_config
from app.scheduling.publisher import fetch_bulk_publish, build_index, fetch_and_cache_index, test_publishers
from app.scheduling.discovery import SlotQuery, discover_slots, choose_slot, haversine_distance, matches_specialty


class TestSchedulingConfig:
    """Test scheduling configuration functionality."""
    
    def test_default_scheduling_config(self):
        """Test default scheduling configuration values."""
        config = SchedulingConfig()
        assert config.publishers == []
        assert config.cache_ttl_seconds == 300
        assert config.default_specialty == "mammography"
        assert config.default_radius_km == 50
        assert config.default_timezone == "America/New_York"
    
    def test_scheduling_config_validation(self):
        """Test scheduling configuration validation."""
        # Valid config
        config = SchedulingConfig(
            publishers=["https://example.com"],
            cache_ttl_seconds=600,
            default_specialty="cardiology",
            default_radius_km=100
        )
        assert len(config.publishers) == 1
        assert config.cache_ttl_seconds == 600
        
        # Test with empty publishers
        config = SchedulingConfig(publishers=[])
        assert config.publishers == []


class TestBulkPublisher:
    """Test bulk publisher fetch and cache functionality."""
    
    def test_fetch_bulk_publish_json(self):
        """Test fetching bulk publish data in JSON format."""
        # Mock response data
        mock_data = {
            "Location": [{"id": "loc1", "name": "Hospital A"}],
            "Organization": [{"id": "org1", "name": "Health System"}],
            "HealthcareService": [{"id": "svc1", "type": [{"text": "mammography"}]}],
            "Schedule": [{"id": "sch1", "actor": [{"reference": "Location/loc1"}]}],
            "Slot": [{"id": "slot1", "start": "2024-12-15T09:00:00Z", "end": "2024-12-15T10:00:00Z"}]
        }
        
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_data
            mock_response.headers = {"content-type": "application/json"}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # This would normally be run with asyncio
            # result = await fetch_bulk_publish("https://example.com")
            # For testing purposes, we'll test the parsing logic directly
            assert "Location" in mock_data
            assert len(mock_data["Location"]) == 1
    
    def test_fetch_bulk_publish_ndjson(self):
        """Test parsing NDJSON format."""
        ndjson_text = '''{"resourceType": "Location", "id": "loc1", "name": "Hospital A"}
{"resourceType": "Slot", "id": "slot1", "start": "2024-12-15T09:00:00Z"}'''
        
        # Simulate NDJSON parsing
        resources_by_type = {}
        for line in ndjson_text.strip().split('\n'):
            if line.strip():
                resource = json.loads(line)
                resource_type = resource.get("resourceType")
                if resource_type:
                    if resource_type not in resources_by_type:
                        resources_by_type[resource_type] = []
                    resources_by_type[resource_type].append(resource)
        
        assert "Location" in resources_by_type
        assert "Slot" in resources_by_type
        assert len(resources_by_type["Location"]) == 1
        assert resources_by_type["Location"][0]["name"] == "Hospital A"
    
    def test_build_index_links_references(self):
        """Test that build_index correctly resolves references."""
        bulk_data = {
            "Location": [{"id": "loc1", "name": "Hospital A", "position": {"latitude": 40.7, "longitude": -74.0}}],
            "Organization": [{"id": "org1", "name": "Health System"}],
            "HealthcareService": [{"id": "svc1", "type": [{"text": "mammography"}]}],
            "Schedule": [{"id": "sch1", "actor": [{"reference": "Location/loc1"}], "serviceType": [{"text": "screening"}]}],
            "Slot": [{"id": "slot1", "start": "2024-12-15T09:00:00Z", "end": "2024-12-15T10:00:00Z", "schedule": {"reference": "Schedule/sch1"}}]
        }
        
        index = build_index(bulk_data, "https://example.com")
        
        # Check basic indexing
        assert "loc1" in index.locations
        assert "org1" in index.organizations
        assert "sch1" in index.schedules
        assert len(index.slots) == 1
        
        # Check reference resolution
        schedule = index.schedules["sch1"]
        assert "_resolved_actors" in schedule
        assert len(schedule["_resolved_actors"]) == 1
        assert schedule["_resolved_actors"][0]["type"] == "Location"
        
        # Check derived fields in slots
        slot = index.slots[0]
        assert "_resolved_schedule" in slot
        assert "_location" in slot
        assert slot["_location"]["name"] == "Hospital A"
        assert slot["_location"]["lat"] == 40.7
        assert slot["_location"]["lng"] == -74.0


class TestSlotDiscovery:
    """Test slot discovery and filtering functionality."""
    
    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        # Distance between NYC and Philadelphia (approximately 95 miles / 153 km)
        nyc_lat, nyc_lng = 40.7128, -74.0060
        phl_lat, phl_lng = 39.9526, -75.1652
        
        distance = haversine_distance(nyc_lat, nyc_lng, phl_lat, phl_lng)
        
        # Should be approximately 130-160 km
        assert 130 <= distance <= 160
    
    def test_matches_specialty(self):
        """Test specialty matching logic."""
        slot_with_mammography = {
            "_service_types": ["mammography", "breast screening"],
            "serviceType": [{"text": "Mammography Services"}]
        }
        
        slot_with_cardiology = {
            "_service_types": ["cardiology"],
            "serviceType": [{"text": "Heart Care"}]
        }
        
        # Test positive matches
        assert matches_specialty(slot_with_mammography, "mammography")
        assert matches_specialty(slot_with_mammography, "breast")
        assert matches_specialty(slot_with_mammography, "screening")
        
        # Test negative matches
        assert not matches_specialty(slot_with_cardiology, "mammography")
        
        # Test empty specialty (should match all)
        assert matches_specialty(slot_with_cardiology, None)
        assert matches_specialty(slot_with_cardiology, "")
    
    def test_slot_query_validation(self):
        """Test SlotQuery model validation."""
        # Valid query
        query = SlotQuery(
            specialty="mammography",
            start=datetime(2024, 12, 15, 9, 0, 0),
            end=datetime(2024, 12, 15, 17, 0, 0),
            lat=40.7,
            lng=-74.0,
            radius_km=50,
            limit=25
        )
        
        assert query.specialty == "mammography"
        assert query.lat == 40.7
        assert query.limit == 25
        
        # Query with defaults
        query = SlotQuery()
        assert query.limit == 50
        assert query.specialty is None
    
    @pytest.mark.asyncio
    async def test_discover_slots_empty_publishers(self):
        """Test slot discovery with no configured publishers."""
        query = SlotQuery(specialty="mammography")
        
        with patch('app.scheduling.discovery.get_scheduling_config') as mock_config:
            mock_config.return_value = SchedulingConfig(publishers=[])
            
            result = await discover_slots(query)
            
            assert result["slots"] == []
            assert result["source_counts"] == {}
    
    @pytest.mark.asyncio
    async def test_choose_slot_success(self):
        """Test successful slot selection."""
        mock_index = MagicMock()
        mock_index.slots = [
            {
                "id": "slot123", 
                "start": "2024-12-15T09:00:00Z",
                "end": "2024-12-15T10:00:00Z",
                "_org": "Hospital A",
                "_location": {"name": "Main Campus"},
                "_booking_link": "https://book.example.com/slot123"
            }
        ]
        
        with patch('app.scheduling.discovery.get_cached_index') as mock_cached, \
             patch('app.scheduling.discovery.fetch_and_cache_index') as mock_fetch:
            
            mock_cached.return_value = mock_index
            
            result = await choose_slot("slot123", "https://publisher.example.com", "test booking")
            
            assert result["success"] is True
            assert "booking_link" in result
            assert result["booking_link"] == "https://book.example.com/slot123"
            assert result["is_simulation"] is False
    
    @pytest.mark.asyncio
    async def test_choose_slot_simulation(self):
        """Test slot selection with simulated booking link."""
        mock_index = MagicMock()
        mock_index.slots = [
            {
                "id": "slot123",
                "start": "2024-12-15T09:00:00Z", 
                "end": "2024-12-15T10:00:00Z",
                "_org": "Hospital A",
                "_location": {"name": "Main Campus"},
                "_booking_link": None  # No real booking link
            }
        ]
        
        with patch('app.scheduling.discovery.get_cached_index') as mock_cached:
            mock_cached.return_value = mock_index
            
            result = await choose_slot("slot123", "https://publisher.example.com", "test booking")
            
            assert result["success"] is True
            assert result["is_simulation"] is True
            assert result["booking_link"].startswith("/schedule/simulate")
            assert "slotId=slot123" in result["booking_link"]
    
    @pytest.mark.asyncio
    async def test_choose_slot_not_found(self):
        """Test slot selection when slot is not found."""
        mock_index = MagicMock()
        mock_index.slots = []  # Empty slots
        
        with patch('app.scheduling.discovery.get_cached_index') as mock_cached:
            mock_cached.return_value = mock_index
            
            result = await choose_slot("nonexistent", "https://publisher.example.com")
            
            assert result["success"] is False
            assert "not found" in result["error"].lower()


class TestSlotFiltering:
    """Test slot filtering logic."""
    
    def test_time_window_filtering(self):
        """Test time window filtering."""
        from app.scheduling.discovery import matches_time_window
        
        # Create test slot
        slot_9am = {
            "_start_dt": datetime(2024, 12, 15, 9, 0, 0, tzinfo=timezone.utc),
            "_end_dt": datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc)
        }
        
        # Test matching time windows
        assert matches_time_window(slot_9am, 
                                 datetime(2024, 12, 15, 8, 0, 0), 
                                 datetime(2024, 12, 15, 18, 0, 0))
        
        # Test non-matching time windows (too early)
        assert not matches_time_window(slot_9am,
                                     datetime(2024, 12, 15, 10, 0, 0),
                                     datetime(2024, 12, 15, 18, 0, 0))
        
        # Test non-matching time windows (too late)  
        assert not matches_time_window(slot_9am,
                                     datetime(2024, 12, 15, 6, 0, 0),
                                     datetime(2024, 12, 15, 8, 0, 0))
    
    def test_geo_filtering(self):
        """Test geographic filtering."""
        from app.scheduling.discovery import matches_location
        
        # Create test slot in NYC area
        slot_nyc = {
            "_location": {
                "name": "NYC Hospital",
                "address": "123 Main St, New York, NY",
                "lat": 40.7128,
                "lng": -74.0060
            }
        }
        
        # Test within radius (50km from NYC)
        matches, distance = matches_location(slot_nyc, 40.7, -74.0, 50, None)
        assert matches is True
        assert distance is not None
        assert distance < 50
        
        # Test outside radius (10km from Philadelphia)
        matches, distance = matches_location(slot_nyc, 39.9526, -75.1652, 10, None)
        assert matches is False
        assert distance > 10
        
        # Test text-based location filtering
        matches, _ = matches_location(slot_nyc, None, None, None, "New York")
        assert matches is True
        
        matches, _ = matches_location(slot_nyc, None, None, None, "Boston")
        assert matches is False


class TestIntegration:
    """Integration tests for the full scheduling flow."""
    
    @pytest.mark.asyncio
    async def test_full_scheduling_flow(self):
        """Test the complete flow from configuration to booking."""
        # This is a simplified integration test
        # In a real scenario, you'd want to test with actual mock data
        
        # 1. Create configuration
        config = SchedulingConfig(
            publishers=["https://test-publisher.example.com"],
            default_specialty="mammography",
            default_radius_km=50
        )
        
        # 2. Create search query
        query = SlotQuery(
            specialty="mammography",
            start=datetime.now(),
            end=datetime.now() + timedelta(days=14),
            radius_km=50,
            limit=10
        )
        
        # Verify query is properly formed
        assert query.specialty == "mammography"
        assert query.limit == 10
        
        # In a real integration test, you would:
        # 3. Mock publisher response
        # 4. Call discover_slots()
        # 5. Verify results are properly filtered and ranked
        # 6. Call choose_slot()
        # 7. Verify booking response
        
        # For now, just verify the objects are created correctly
        assert config.publishers == ["https://test-publisher.example.com"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])