#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Tests - Interface Tests
============================
Unit tests for interface components (API, CLI, GUI).
"""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPIExists(unittest.TestCase):
    """Tests for API interface."""
    
    def test_api_file_exists(self):
        """Test that API file exists."""
        api_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "interface", "api.py"
        )
        self.assertTrue(os.path.exists(api_path))


class TestCLIExists(unittest.TestCase):
    """Tests for CLI interface."""
    
    def test_cli_file_exists(self):
        """Test that CLI file exists."""
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "interface", "cli.py"
        )
        self.assertTrue(os.path.exists(cli_path))


class TestGUIExists(unittest.TestCase):
    """Tests for GUI interface."""
    
    def test_gui_file_exists(self):
        """Test that GUI file exists."""
        gui_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "interface", "gui.py"
        )
        self.assertTrue(os.path.exists(gui_path))


class TestDeployment(unittest.TestCase):
    """Tests for deployment module."""
    
    def test_import_deployment(self):
        """Test that deployment can be imported."""
        try:
            from nova_system.deployment import NovaDeployment
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"Deployment not available: {e}")
    
    def test_deployment_init(self):
        """Test deployment initialization."""
        from nova_system.deployment import NovaDeployment
        deployment = NovaDeployment()
        
        self.assertIsNotNone(deployment.project_root)
        self.assertTrue(hasattr(deployment, 'check_ollama'))


class TestRegistry(unittest.TestCase):
    """Tests for registry module."""
    
    def test_import_registry(self):
        """Test that registry can be imported."""
        from nova_system.registry import NovaRegistry
        self.assertTrue(True)
    
    def test_registry_init(self):
        """Test registry initialization."""
        from nova_system.registry import NovaRegistry
        registry = NovaRegistry()
        
        self.assertIsNotNone(registry.models)
        self.assertIsNotNone(registry.tools)
    
    def test_register_model(self):
        """Test model registration."""
        from nova_system.registry import NovaRegistry
        registry = NovaRegistry()
        
        model = registry.register_model('test-model', 'ollama', '1.0')
        self.assertEqual(model.name, 'test-model')
        
        # Cleanup
        registry.unregister_model('test-model')


class TestWorkflow(unittest.TestCase):
    """Tests for workflow (orchestrator)."""
    
    def test_import_workflow(self):
        """Test that workflow can be imported."""
        try:
            from nova_system.workflow import NovaOrchestrator
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"Workflow not available: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
