"""Tests - SecurityManager v2"""
import sys, unittest, json, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCommandValidator(unittest.TestCase):

    def setUp(self):
        from core.security_manager import CommandValidator
        self.v = CommandValidator()

    def test_safe_command_passes(self):
        self.assertTrue(self.v.validate_text("ouvre Word s'il te plaît"))

    def test_safe_weather_passes(self):
        self.assertTrue(self.v.validate_text("quelle est la météo à Paris"))

    def test_rm_rf_blocked(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_text("rm -rf /home")

    def test_del_blocked(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_text("del /s /f C:\\Windows")

    def test_eval_blocked(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_text("eval(malicious_code())")

    def test_sql_injection_blocked(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_text("DROP TABLE utilisateurs")

    def test_allowed_app_word(self):
        self.assertTrue(self.v.validate_app_name("word"))

    def test_allowed_app_chrome(self):
        self.assertTrue(self.v.validate_app_name("chrome"))

    def test_blocked_app(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_app_name("malware.exe")

    def test_system_path_blocked(self):
        from core.exceptions import CommandBlockedError
        with self.assertRaises(CommandBlockedError):
            self.v.validate_file_path("C:\\Windows\\System32\\cmd.exe")

    def test_safe_path_allowed(self):
        self.assertTrue(self.v.validate_file_path("C:\\Users\\Alice\\Documents\\rapport.docx"))


class TestApiKeyVault(unittest.TestCase):

    def setUp(self):
        from core.security_manager import ApiKeyVault
        self.vault = ApiKeyVault()

    def test_get_missing_key(self):
        import os
        env_backup = os.environ.pop("OPENAI_API_KEY", None)
        result = self.vault.get("openai")
        if env_backup:
            os.environ["OPENAI_API_KEY"] = env_backup
        self.assertIsNone(result)

    def test_get_existing_key(self):
        import os
        os.environ["OPENWEATHER_API_KEY"] = "test_weather_key"
        result = self.vault.get("openweather")
        del os.environ["OPENWEATHER_API_KEY"]
        self.assertEqual(result, "test_weather_key")

    def test_is_available_false(self):
        import os
        os.environ.pop("OPENAI_API_KEY", None)
        self.assertFalse(self.vault.is_available("openai"))

    def test_mask_key(self):
        masked = self.vault.mask("sk-abcdefghijklmnop")
        self.assertIn("...", masked)
        self.assertTrue(masked.startswith("sk-a"))
        self.assertNotEqual(masked, "sk-abcdefghijklmnop")

    def test_mask_short_key(self):
        masked = self.vault.mask("ab")
        self.assertEqual(masked, "***")

    def test_unknown_service(self):
        result = self.vault.get("unknown_service_xyz")
        self.assertIsNone(result)


class TestSecurityManager(unittest.TestCase):

    def _make_security(self, permissions: dict):
        """Crée un SecurityManager avec des permissions en mémoire."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(permissions, tmp)
        tmp.close()

        with patch('core.security_manager.PERMISSIONS_PATH', Path(tmp.name)):
            from core.security_manager import SecurityManager
            sm = SecurityManager.__new__(SecurityManager)
            sm._permissions = {k: v for k, v in permissions.items() if k != "require_confirmation_for"}
            sm._confirmation_required = permissions.get("require_confirmation_for", [])
            from core.security_manager import CommandValidator, ApiKeyVault, AuditLogger
            sm.validator = CommandValidator()
            sm.vault     = ApiKeyVault()
            sm.audit     = MagicMock()

        Path(tmp.name).unlink(missing_ok=True)
        return sm

    def test_allowed_action(self):
        sm = self._make_security({"allow_browser_control": True})
        self.assertTrue(sm.is_allowed("browser_control"))

    def test_denied_action(self):
        sm = self._make_security({"allow_shutdown": False})
        self.assertFalse(sm.is_allowed("shutdown"))

    def test_require_raises_on_denied(self):
        from core.exceptions import PermissionDeniedError
        sm = self._make_security({"allow_shutdown": False})
        with self.assertRaises(PermissionDeniedError):
            sm.require("shutdown")

    def test_require_passes_on_allowed(self):
        sm = self._make_security({"allow_browser_control": True})
        sm.require("browser_control")  # Ne doit pas lever

    def test_needs_confirmation(self):
        sm = self._make_security({
            "allow_shutdown": True,
            "require_confirmation_for": ["shutdown"]
        })
        self.assertTrue(sm.needs_confirmation("shutdown"))

    def test_no_confirmation_needed(self):
        sm = self._make_security({
            "allow_browser_control": True,
            "require_confirmation_for": ["shutdown"]
        })
        self.assertFalse(sm.needs_confirmation("browser_control"))

    def test_validate_command_safe(self):
        sm = self._make_security({})
        self.assertTrue(sm.validate_command("ouvre Word"))

    def test_validate_command_dangerous(self):
        from core.exceptions import CommandBlockedError
        sm = self._make_security({})
        with self.assertRaises(CommandBlockedError):
            sm.validate_command("rm -rf /")

    def test_guard_decorator_allowed(self):
        sm = self._make_security({"allow_browser_control": True})

        @sm.guard("browser_control")
        def open_browser():
            return "opened"

        self.assertEqual(open_browser(), "opened")

    def test_guard_decorator_blocked(self):
        from core.exceptions import PermissionDeniedError
        sm = self._make_security({"allow_shutdown": False})

        @sm.guard("shutdown")
        def shutdown():
            return "bye"

        with self.assertRaises(PermissionDeniedError):
            shutdown()


class TestHealthMonitor(unittest.TestCase):

    def setUp(self):
        from core.health_monitor import HealthMonitor
        self.monitor = HealthMonitor(check_interval=99999)

    def test_register_module(self):
        self.monitor.register("test_mod", lambda: None)
        self.assertIn("test_mod", self.monitor._modules)

    def test_check_ok_module(self):
        self.monitor.register("ok_mod", lambda: None)
        self.monitor._run_checks()
        self.assertEqual(self.monitor._modules["ok_mod"].status, "ok")

    def test_check_failing_module(self):
        def fail(): raise RuntimeError("Test error")
        self.monitor.register("fail_mod", fail)
        self.monitor._run_checks()
        self.assertIn(self.monitor._modules["fail_mod"].status, ["degraded", "down"])

    def test_overall_healthy(self):
        self.monitor.register("m1", lambda: None)
        self.monitor.register("m2", lambda: None)
        self.monitor._run_checks()
        self.assertEqual(self.monitor._overall_status(), "healthy")

    def test_overall_degraded(self):
        self.monitor.register("good", lambda: None)
        def fail(): raise RuntimeError("fail")
        self.monitor.register("bad", fail)
        self.monitor._run_checks()
        status = self.monitor._overall_status()
        self.assertIn(status, ["degraded", "critical"])

    def test_report_structure(self):
        self.monitor.register("mod", lambda: None)
        self.monitor._run_checks()
        report = self.monitor.get_report()
        self.assertIn("timestamp", report)
        self.assertIn("modules", report)
        self.assertIn("overall", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
