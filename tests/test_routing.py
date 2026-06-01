"""Tests - routage des actions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTaskRouterCompatibility(unittest.TestCase):

    def test_registered_action_accepts_router_keywords(self):
        from core.action_registry import ActionRegistry
        from core.task_router import TaskRouter

        registry = ActionRegistry()
        router = TaskRouter()

        def handler(entities=None, context=None):
            return f"ok:{entities['value']}:{context['source']}"

        registry.register("TEST_ACTION", handler)
        router.register(
            "TEST_ACTION",
            lambda entities=None, context=None, n="TEST_ACTION":
                registry.execute(n, entities, context)
        )

        result = router.route(
            "TEST_ACTION",
            {"value": "route"},
            context={"source": "test"}
        )

        self.assertEqual(result, "ok:route:test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
