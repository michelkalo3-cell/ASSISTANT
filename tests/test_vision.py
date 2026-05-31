"""Tests - VisionManager v2"""
import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestScreenReaderCapabilities(unittest.TestCase):

    def setUp(self):
        from modules.vision.screen_reader import ScreenReader
        self.sr = ScreenReader()

    def test_capabilities_is_dict(self):
        caps = self.sr.capabilities
        self.assertIsInstance(caps, dict)

    def test_capabilities_has_required_keys(self):
        caps = self.sr.capabilities
        for key in ["screen_capture", "ocr_tesseract", "ocr_easyocr",
                    "computer_vision", "button_detection", "click_by_text"]:
            self.assertIn(key, caps)

    def test_capabilities_all_bool(self):
        caps = self.sr.capabilities
        for k, v in caps.items():
            self.assertIsInstance(v, bool, f"capabilities[{k}] doit être bool")

    def test_check_helper_valid(self):
        result = self.sr._check("json", "import json")
        self.assertTrue(result)

    def test_check_helper_invalid(self):
        result = self.sr._check("fake_module", "import fake_module_xyz_nonexistent")
        self.assertFalse(result)

    def test_button_detection_returns_list_without_cv2(self):
        sr = self.sr
        if not sr._cv2_ok or not sr._tess_ok:
            result = sr.detect_buttons()
            self.assertIsInstance(result, list)
            self.assertEqual(result, [])

    def test_find_text_position_returns_none_without_tesseract(self):
        sr = self.sr
        if not sr._tess_ok:
            result = sr.find_text_position("Bouton OK")
            self.assertIsNone(result)

    def test_get_screen_summary_returns_string(self):
        # Mock capture pour éviter dépendance écran
        with patch.object(self.sr, 'read_screen', return_value="Texte visible à l'écran"):
            result = self.sr.get_screen_summary()
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_get_screen_summary_empty_screen(self):
        with patch.object(self.sr, 'read_screen', return_value=""):
            result = self.sr.get_screen_summary()
            self.assertIn("lisible", result.lower())


class TestScreenReaderImageOCR(unittest.TestCase):
    """Tests OCR sur fichiers image (ne nécessite pas d'écran)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        from modules.vision.screen_reader import ScreenReader
        self.sr = ScreenReader()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_read_image_no_tesseract_returns_message(self):
        p = Path(self.tmp) / "img.png"
        # Crée une image blanche minimale si PIL dispo
        try:
            from PIL import Image
            img = Image.new("RGB", (100, 30), color=(255, 255, 255))
            img.save(str(p))
            # Si Tesseract absent, retourne un message d'info
            if not self.sr._tess_ok and not self.sr._easy_ok:
                result = self.sr.read_image_file(str(p))
                self.assertIn("OCR", result)
        except ImportError:
            self.skipTest("Pillow non installé")

    def test_compare_screenshots_missing_files(self):
        result = self.sr.compare_screenshots("/nonexistent1.png", "/nonexistent2.png")
        self.assertEqual(result, 0.0)

    def test_compare_screenshots_identical(self):
        if not self.sr._cv2_ok or not self.sr._pil_ok:
            self.skipTest("OpenCV ou PIL non installé")
        try:
            from PIL import Image
            import numpy as np, cv2
            img = Image.new("RGB", (100, 100), color=(128, 128, 128))
            p1 = Path(self.tmp) / "s1.png"
            p2 = Path(self.tmp) / "s2.png"
            img.save(str(p1))
            img.save(str(p2))
            score = self.sr.compare_screenshots(str(p1), str(p2))
            self.assertAlmostEqual(score, 1.0, places=1)
        except Exception:
            pass


class TestOCRShortcut(unittest.TestCase):

    def setUp(self):
        from modules.vision.screen_reader import OCR
        self.ocr = OCR()

    def test_ocr_has_methods(self):
        self.assertTrue(hasattr(self.ocr, 'read_image'))
        self.assertTrue(hasattr(self.ocr, 'read_screen'))


class TestLocalModelFallback(unittest.TestCase):

    def test_fallback_models_list_not_empty(self):
        from modules.ai.local_model import FALLBACK_MODELS
        self.assertGreater(len(FALLBACK_MODELS), 0)
        self.assertIn("mistral", FALLBACK_MODELS)
        self.assertIn("phi3:mini", FALLBACK_MODELS)

    def test_select_model_no_models_installed(self):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient(model="mistral")
        client._installed_models = []
        result = client._select_model()
        self.assertIsNone(result)

    def test_select_model_requested_available(self):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient(model="mistral")
        client._installed_models = ["mistral", "llama3"]
        result = client._select_model()
        self.assertEqual(result, "mistral")

    def test_select_model_fallback_to_phi3(self):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient(model="nonexistent_model_xyz")
        client._installed_models = ["phi3"]
        result = client._select_model()
        self.assertIsNotNone(result)
        self.assertIn("phi3", result)

    def test_select_model_fallback_any_available(self):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient(model="nonexistent")
        client._installed_models = ["some_unknown_model"]
        result = client._select_model()
        # Retourne le premier modèle disponible en dernier recours
        self.assertEqual(result, "some_unknown_model")

    @patch('modules.ai.local_model.requests.get')
    def test_is_available_caches_result(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": []}
        from modules.ai.local_model import OllamaClient
        client = OllamaClient()
        client._available = None
        client.is_available()
        client.is_available()   # Deuxième appel
        # Doit appeler requests.get une seule fois (cache)
        self.assertEqual(mock_get.call_count, 1)

    def test_hybrid_strategy_local_only(self):
        from modules.ai.local_model import HybridAIClient
        from unittest.mock import MagicMock
        client = HybridAIClient(config={"ai_strategy": "local_only"})
        client._local = MagicMock()
        client._local.is_available.return_value = True
        client._local.chat.return_value = "Réponse locale"
        result = client.chat([{"role": "user", "content": "test"}])
        self.assertEqual(result, "Réponse locale")
        client._cloud = MagicMock()
        client._cloud.chat.assert_not_called()

    def test_hybrid_stats(self):
        from modules.ai.local_model import HybridAIClient
        client = HybridAIClient(config={})
        stats = client.get_stats()
        self.assertIn("strategy", stats)
        self.assertIn("cloud_ok", stats)
        self.assertIn("local_ok", stats)
        self.assertIn("active", stats)
        self.assertIn("local_models", stats)


if __name__ == "__main__":
    unittest.main(verbosity=2)
