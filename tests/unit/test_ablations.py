"""Tests for I5 ablation interfaces."""
import pytest
from aftbench.interfaces import (
    I5FullAFTInterface,
    I5MinusSelectiveDiscovery,
    I5MinusResumableInvocation,
    I5MinusObservableExecution,
    I5MinusStructuredOutput,
    I5MinusSideEffectContract,
    I5MinusDurableState,
    I5MinusVerification,
    ABLATION_NAMES,
    create_ablation_interface,
)


class TestAblationInterfaces:
    """Test that each ablation removes exactly one feature."""
    
    def test_all_ablation_names_exist(self):
        """Verify all 7 ablation names are defined."""
        assert len(ABLATION_NAMES) == 7
        expected = {
            "I5-minus-selective-discovery",
            "I5-minus-resumable-invocation",
            "I5-minus-observable-execution",
            "I5-minus-structured-output",
            "I5-minus-side-effect-contract",
            "I5-minus-durable-state",
            "I5-minus-verification",
        }
        assert set(ABLATION_NAMES) == expected
    
    def test_create_ablation_interface(self):
        """Test factory function creates correct interfaces."""
        for name in ABLATION_NAMES:
            iface = create_ablation_interface(name)
            assert iface.condition_name == name
            assert hasattr(iface, 'features')
            assert hasattr(iface, 'get_feature_flags')
    
    def test_each_ablation_changes_one_feature(self):
        """Verify each ablation changes exactly one feature flag."""
        full_features = I5FullAFTInterface()
        
        # I5-minus-selective-discovery
        iface = I5MinusSelectiveDiscovery()
        flags = iface.get_feature_flags()
        assert flags['selective_discovery'] is False
        assert all(flags[k] is True for k in flags if k != 'selective_discovery')
        
        # I5-minus-resumable-invocation
        iface = I5MinusResumableInvocation()
        flags = iface.get_feature_flags()
        assert flags['resumable_invocation'] is False
        assert all(flags[k] is True for k in flags if k != 'resumable_invocation')
        
        # I5-minus-observable-execution
        iface = I5MinusObservableExecution()
        flags = iface.get_feature_flags()
        assert flags['observable_execution'] is False
        assert all(flags[k] is True for k in flags if k != 'observable_execution')
        
        # I5-minus-structured-output
        iface = I5MinusStructuredOutput()
        flags = iface.get_feature_flags()
        assert flags['structured_output'] is False
        assert all(flags[k] is True for k in flags if k != 'structured_output')
        
        # I5-minus-side-effect-contract
        iface = I5MinusSideEffectContract()
        flags = iface.get_feature_flags()
        assert flags['side_effect_contract'] is False
        assert all(flags[k] is True for k in flags if k != 'side_effect_contract')
        
        # I5-minus-durable-state
        iface = I5MinusDurableState()
        flags = iface.get_feature_flags()
        assert flags['durable_state'] is False
        assert all(flags[k] is True for k in flags if k != 'durable_state')
        
        # I5-minus-verification
        iface = I5MinusVerification()
        flags = iface.get_feature_flags()
        assert flags['verification'] is False
        assert all(flags[k] is True for k in flags if k != 'verification')
    
    def test_ablation_preserves_backend_parity(self, tmp_path):
        """Verify ablations use same backend operations as I5."""
        from aftbench.worlds.enterprise_records import EnterpriseRecordsWorld
        
        world = EnterpriseRecordsWorld()
        world.reset(seed=42)
        
        # Test that I5 and ablation both call apply_effect
        i5 = I5FullAFTInterface()
        ablation = I5MinusSelectiveDiscovery()
        
        # Both should be able to invoke
        i5_result = i5.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, world)
        ablation_result = ablation.invoke("crm.create_record", {"record_type": "contact", "fields": {}}, world)
        
        # Both should succeed
        assert i5_result.get("status") in ("success", "committed")
        assert ablation_result.get("status") in ("success", "committed")
    
    def test_removed_feature_unavailable(self):
        """Test that removed features are actually unavailable."""
        # I5-minus-resumable-invocation should not have working resume
        iface = I5MinusResumableInvocation()
        result = iface.resume("test-invocation-id")
        assert result.get("status") == "error"
        assert "not available" in result.get("error", "").lower()
        
        # I5-minus-observable-execution should not have working get_status
        iface = I5MinusObservableExecution()
        result = iface.get_status("test-invocation-id")
        assert result.get("status") == "error"
        assert "not available" in result.get("error", "").lower()
        
        # I5-minus-durable-state should not have working reconcile
        iface = I5MinusDurableState()
        result = iface.reconcile("test-invocation-id")
        assert result.get("status") == "error"
        assert "not available" in result.get("error", "").lower()
    
    def test_unrelated_features_enabled(self):
        """Test that unrelated features remain enabled in ablations."""
        # I5-minus-selective-discovery should still have all other features
        iface = I5MinusSelectiveDiscovery()
        assert hasattr(iface, 'resume')
        assert hasattr(iface, 'reconcile')
        assert hasattr(iface, 'get_evidence')
        
        # I5-minus-resumable-invocation should still have discovery
        iface = I5MinusResumableInvocation()
        assert hasattr(iface, 'discover')
        assert hasattr(iface, 'get_schema')


class TestAblationFeatureMatrix:
    """Test ablation feature matrix generation."""
    
    def test_feature_matrix_generation(self, tmp_path):
        """Generate and validate ablation feature matrix."""
        import csv
        
        matrix_path = tmp_path / "ablation_feature_matrix.csv"
        
        with open(matrix_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "condition",
                "selective_discovery",
                "resumable_invocation",
                "observable_execution",
                "structured_output",
                "side_effect_contract",
                "durable_state",
                "verification",
            ])
            
            # I5-full (all features enabled)
            writer.writerow(["I5-full", True, True, True, True, True, True, True])
            
            # All ablations
            for name in ABLATION_NAMES:
                iface = create_ablation_interface(name)
                flags = iface.get_feature_flags()
                writer.writerow([
                    name,
                    flags['selective_discovery'],
                    flags['resumable_invocation'],
                    flags['observable_execution'],
                    flags['structured_output'],
                    flags['side_effect_contract'],
                    flags['durable_state'],
                    flags['verification'],
                ])
        
        # Verify matrix
        with open(matrix_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Should have 8 rows (I5-full + 7 ablations)
            assert len(rows) == 8
            
            # I5-full should have all True
            i5_full = rows[0]
            assert i5_full['condition'] == 'I5-full'
            assert all(i5_full[k] == 'True' for k in i5_full if k != 'condition')
            
            # Each ablation should have exactly one False
            for row in rows[1:]:
                false_count = sum(1 for k in row if k != 'condition' and row[k] == 'False')
                assert false_count == 1, f"{row['condition']} has {false_count} False values, expected 1"
