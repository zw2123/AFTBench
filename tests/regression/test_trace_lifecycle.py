"""Regression tests for trace lifecycle events."""
import pytest
import json
from pathlib import Path


class TestTraceLifecycleEvents:
    """Test that traces contain required lifecycle events and identifiers."""
    
    def test_lifecycle_events_present(self, tmp_path):
        """Verify all required lifecycle events are present in traces."""
        from aftbench.runner import BenchmarkRunner
        from aftbench.config import BenchmarkConfig
        from aftbench.trace import TraceWriter
        
        # Create a minimal config
        config = BenchmarkConfig(
            profile="test",
            output_dir=str(tmp_path),
            worlds=["enterprise_records"],
            interfaces=["I0"],
            faults=["lost_response_after_effect"],
            max_tasks_per_world=1,
            seeds=[42],
        )
        
        # Run a single task
        runner = BenchmarkRunner(config)
        results = runner.run_profile()
        
        # Check traces
        traces_path = tmp_path / "traces.jsonl"
        assert traces_path.exists(), "traces.jsonl should exist"
        
        events = []
        with open(traces_path) as f:
            for line in f:
                events.append(json.loads(line))
        
        # Check for required lifecycle events
        event_types = [e['event_type'] for e in events]
        
        required_events = [
            'REQUEST_ACCEPTED',
            'BACKEND_STARTED',
            'RESPONSE_GENERATED',
        ]
        
        for req in required_events:
            assert req in event_types, f"Required event {req} not found in traces"
        
        # For lost_response_after_effect, should have EFFECT_COMMITTED and RESPONSE_DROPPED
        if any(e.get('fault_id') == 'lost_response_after_effect' for e in events):
            # Check if effect was committed
            has_commit = 'EFFECT_COMMITTED' in event_types
            has_drop = 'RESPONSE_DROPPED' in event_types
            
            # If effect committed, should have RESPONSE_DROPPED
            if has_commit:
                assert has_drop, "RESPONSE_DROPPED should follow EFFECT_COMMITTED for lost_response fault"
    
    def test_identifiers_present(self, tmp_path):
        """Verify all required identifiers are present in lifecycle events."""
        from aftbench.runner import BenchmarkRunner
        from aftbench.config import BenchmarkConfig
        
        config = BenchmarkConfig(
            profile="test",
            output_dir=str(tmp_path),
            worlds=["enterprise_records"],
            interfaces=["I0"],
            faults=["none"],
            max_tasks_per_world=1,
            seeds=[42],
        )
        
        runner = BenchmarkRunner(config)
        results = runner.run_profile()
        
        traces_path = tmp_path / "traces.jsonl"
        events = []
        with open(traces_path) as f:
            for line in f:
                events.append(json.loads(line))
        
        # Check lifecycle events have identifiers
        lifecycle_events = [e for e in events if e['event_type'] in 
                          ['REQUEST_ACCEPTED', 'BACKEND_STARTED', 'EFFECT_COMMITTED', 
                           'RESPONSE_GENERATED', 'RESPONSE_DROPPED']]
        
        assert len(lifecycle_events) > 0, "Should have lifecycle events"
        
        required_ids = ['invocation_id', 'logical_effect_id', 'backend_operation_id', 'resource_id']
        
        for event in lifecycle_events:
            for req_id in required_ids:
                assert event.get(req_id) is not None, \
                    f"Lifecycle event {event['event_type']} missing {req_id}"
    
    def test_event_ordering(self, tmp_path):
        """Verify lifecycle events occur in correct order."""
        from aftbench.runner import BenchmarkRunner
        from aftbench.config import BenchmarkConfig
        
        config = BenchmarkConfig(
            profile="test",
            output_dir=str(tmp_path),
            worlds=["enterprise_records"],
            interfaces=["I0"],
            faults=["none"],
            max_tasks_per_world=1,
            seeds=[42],
        )
        
        runner = BenchmarkRunner(config)
        results = runner.run_profile()
        
        traces_path = tmp_path / "traces.jsonl"
        events = []
        with open(traces_path) as f:
            for line in f:
                events.append(json.loads(line))
        
        # Get lifecycle events in order
        lifecycle_events = [e for e in events if e['event_type'] in 
                          ['REQUEST_ACCEPTED', 'BACKEND_STARTED', 'EFFECT_COMMITTED', 
                           'RESPONSE_GENERATED']]
        
        if len(lifecycle_events) >= 3:
            # Should have REQUEST_ACCEPTED before BACKEND_STARTED
            req_idx = next((i for i, e in enumerate(lifecycle_events) 
                          if e['event_type'] == 'REQUEST_ACCEPTED'), -1)
            backend_idx = next((i for i, e in enumerate(lifecycle_events) 
                              if e['event_type'] == 'BACKEND_STARTED'), -1)
            
            if req_idx >= 0 and backend_idx >= 0:
                assert req_idx < backend_idx, \
                    "REQUEST_ACCEPTED should occur before BACKEND_STARTED"
            
            # Should have BACKEND_STARTED before RESPONSE_GENERATED
            response_idx = next((i for i, e in enumerate(lifecycle_events) 
                               if e['event_type'] == 'RESPONSE_GENERATED'), -1)
            
            if backend_idx >= 0 and response_idx >= 0:
                assert backend_idx < response_idx, \
                    "BACKEND_STARTED should occur before RESPONSE_GENERATED"
    
    def test_lost_response_semantics(self, tmp_path):
        """Verify lost_response_after_effect has correct semantics."""
        from aftbench.runner import BenchmarkRunner
        from aftbench.config import BenchmarkConfig
        
        config = BenchmarkConfig(
            profile="test",
            output_dir=str(tmp_path),
            worlds=["external_actions"],
            interfaces=["I5"],
            faults=["lost_response_after_effect"],
            max_tasks_per_world=1,
            seeds=[42],
        )
        
        runner = BenchmarkRunner(config)
        results = runner.run_profile()
        
        traces_path = tmp_path / "traces.jsonl"
        events = []
        with open(traces_path) as f:
            for line in f:
                events.append(json.loads(line))
        
        # Find runs with lost_response fault
        lost_response_events = [e for e in events 
                               if e.get('fault_id') == 'lost_response_after_effect']
        
        if lost_response_events:
            # Should have EFFECT_COMMITTED before RESPONSE_DROPPED
            commit_idx = next((i for i, e in enumerate(lost_response_events) 
                             if e['event_type'] == 'EFFECT_COMMITTED'), -1)
            drop_idx = next((i for i, e in enumerate(lost_response_events) 
                           if e['event_type'] == 'RESPONSE_DROPPED'), -1)
            
            if commit_idx >= 0 and drop_idx >= 0:
                assert commit_idx < drop_idx, \
                    "EFFECT_COMMITTED should occur before RESPONSE_DROPPED for lost_response fault"
