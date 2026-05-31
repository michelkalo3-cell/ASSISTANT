"""Tests - SecureVault AES"""
import sys, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_vault(tmp_dir: str):
    import core.vault as v_mod
    orig_v, orig_k = v_mod.VAULT_FILE, v_mod.KEY_FILE
    v_mod.VAULT_FILE = Path(tmp_dir) / "vault.enc"
    v_mod.KEY_FILE   = Path(tmp_dir) / "vault.key"
    v_mod.DATA_DIR   = Path(tmp_dir)
    from core.vault import SecureVault
    vault = SecureVault()
    v_mod.VAULT_FILE, v_mod.KEY_FILE = orig_v, orig_k
    return vault


class TestSecureVault(unittest.TestCase):

    def setUp(self):
        self.tmp   = tempfile.mkdtemp()
        self.vault = _make_vault(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── Stockage / récupération ──────────────────────────────────────────────

    def test_store_and_get(self):
        self.vault.store("openai", "sk-testkey12345678")
        result = self.vault._data.get("openai")
        self.assertEqual(result, "sk-testkey12345678")

    def test_get_returns_stored(self):
        self.vault._data["testservice"] = "myvalue"
        self.assertEqual(self.vault.get("testservice"), "myvalue")

    def test_get_fallback_env(self):
        os.environ["OPENWEATHER_API_KEY"] = "env_weather_key"
        result = self.vault.get("openweather")
        del os.environ["OPENWEATHER_API_KEY"]
        self.assertEqual(result, "env_weather_key")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.vault.get("nonexistent_xyz"))

    def test_store_empty_fails(self):
        result = self.vault.store("svc", "")
        self.assertFalse(result)

    def test_store_whitespace_fails(self):
        result = self.vault.store("svc", "   ")
        self.assertFalse(result)

    # ── Suppression ──────────────────────────────────────────────────────────

    def test_delete_existing(self):
        self.vault._data["tosvc"] = "tovalue"
        result = self.vault.delete("tosvc")
        self.assertTrue(result)
        self.assertNotIn("tosvc", self.vault._data)

    def test_delete_nonexistent(self):
        result = self.vault.delete("doesnotexist")
        self.assertFalse(result)

    # ── Disponibilité ────────────────────────────────────────────────────────

    def test_is_available_true(self):
        self.vault._data["mysvc"] = "mykey"
        self.assertTrue(self.vault.is_available("mysvc"))

    def test_is_available_false(self):
        self.assertFalse(self.vault.is_available("nosvc"))

    # ── Liste des services ────────────────────────────────────────────────────

    def test_list_services_empty(self):
        # Vault vide, pas de variables d'env
        svc = self.vault.list_services()
        self.assertIsInstance(svc, list)

    def test_list_services_includes_stored(self):
        self.vault._data["myapi"] = "key123"
        svc = self.vault.list_services()
        self.assertIn("myapi", svc)

    # ── Masquage ─────────────────────────────────────────────────────────────

    def test_mask_long_key(self):
        masked = self.vault.mask("sk-abcdefghijklmnopqrst")
        self.assertIn("*", masked)
        self.assertTrue(masked.startswith("sk-a"))
        self.assertTrue(masked.endswith("qrst"))

    def test_mask_short_key(self):
        self.assertEqual(self.vault.mask("short"), "***")

    def test_mask_empty(self):
        self.assertEqual(self.vault.mask(""), "***")

    # ── Chiffrement ──────────────────────────────────────────────────────────

    def test_data_encrypted_on_disk(self):
        """Le fichier vault.enc ne doit pas contenir la clé en clair."""
        self.vault._data["apikey"] = "my_secret_value_12345"
        self.vault._save()
        vault_file = Path(self.tmp) / "vault.enc"
        if vault_file.exists():
            raw = vault_file.read_bytes()
            self.assertNotIn(b"my_secret_value_12345", raw)

    def test_key_file_permissions(self):
        """Le fichier vault.key doit avoir des permissions restrictives."""
        key_file = Path(self.tmp) / "vault.key"
        if key_file.exists():
            import stat
            mode = oct(stat.S_IMODE(os.stat(key_file).st_mode))
            # Sur Unix, doit être 0o600
            if os.name != 'nt':
                self.assertEqual(mode, '0o600')

    # ── Migrate from env ─────────────────────────────────────────────────────

    def test_migrate_from_env(self):
        os.environ["OPENAI_API_KEY"] = "sk-migrated-key"
        count = self.vault.migrate_from_env()
        os.environ.pop("OPENAI_API_KEY", None)
        self.assertGreaterEqual(count, 1)

    # ── Summary ──────────────────────────────────────────────────────────────

    def test_summary_empty(self):
        summary = self.vault.summary()
        self.assertIn("Vault", summary)

    def test_summary_with_keys(self):
        self.vault._data["svc1"] = "key1"
        self.vault._data["svc2"] = "key2"
        summary = self.vault.summary()
        self.assertIn("2", summary)


class TestGetVaultSingleton(unittest.TestCase):

    def test_singleton(self):
        from core.vault import get_vault
        v1 = get_vault()
        v2 = get_vault()
        self.assertIs(v1, v2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
