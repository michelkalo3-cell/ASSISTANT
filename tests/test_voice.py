"""Tests - Modules voix v2"""
import sys, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSynthesizer(unittest.TestCase):

    def test_init_without_crash(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        # Peut avoir engine=None si pyttsx3 absent, ne doit pas planter

    def test_speak_no_engine(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s._engine = None
        s.speak("Test message")   # Doit être silencieux, pas d'exception

    def test_speak_empty_string(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s._engine = None
        s.speak("")   # Ne doit pas planter

    def test_set_volume_clamped_high(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s.set_volume(1.5)
        self.assertEqual(s.volume, 1.0)

    def test_set_volume_clamped_low(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s.set_volume(-0.5)
        self.assertEqual(s.volume, 0.0)

    def test_set_volume_valid(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s.set_volume(0.7)
        self.assertAlmostEqual(s.volume, 0.7)

    def test_set_rate(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        s.set_rate(200)
        self.assertEqual(s.rate, 200)

    def test_list_voices_returns_list(self):
        from modules.voice.synthesis import Synthesizer
        s = Synthesizer()
        voices = s.list_voices()
        self.assertIsInstance(voices, list)

    def test_speak_async_returns_thread(self):
        from modules.voice.synthesis import Synthesizer
        import threading
        s = Synthesizer()
        s._engine = None
        t = s.speak_async("Test")
        self.assertIsInstance(t, threading.Thread)
        t.join(timeout=2)


class TestWakeWordDetector(unittest.TestCase):

    def setUp(self):
        from modules.voice.wake_word import WakeWordDetector
        self.detector = WakeWordDetector(wake_word="charamou")

    def test_detect_present(self):
        self.assertTrue(self.detector.check_text("hey charamou ouvre Word"))

    def test_detect_absent(self):
        self.assertFalse(self.detector.check_text("bonjour comment ça va"))

    def test_case_insensitive(self):
        self.assertTrue(self.detector.check_text("CHARAMOU aide-moi"))

    def test_callback_called(self):
        called = []
        from modules.voice.wake_word import WakeWordDetector
        d = WakeWordDetector(wake_word="test", on_detected=lambda: called.append(True))
        d.check_text("c'est un test maintenant")
        self.assertTrue(len(called) > 0)

    def test_callback_not_called_when_absent(self):
        called = []
        from modules.voice.wake_word import WakeWordDetector
        d = WakeWordDetector(wake_word="secret", on_detected=lambda: called.append(True))
        d.check_text("bonjour tout le monde")
        self.assertEqual(len(called), 0)

    def test_returns_bool(self):
        result = self.detector.check_text("quelque chose")
        self.assertIsInstance(result, bool)

    def test_stop_no_crash(self):
        self.detector.stop()   # Ne doit pas planter


class TestOllamaClient(unittest.TestCase):

    def test_init(self):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient(model="mistral")
        self.assertEqual(client.requested_model, "mistral")

    @patch('modules.ai.local_model.requests.get')
    def test_is_available_true(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "mistral"}]}
        from modules.ai.local_model import OllamaClient
        client = OllamaClient()
        client._available = None
        self.assertTrue(client.is_available())

    @patch('modules.ai.local_model.requests.get', side_effect=Exception("connexion refusée"))
    def test_is_available_false(self, mock_get):
        from modules.ai.local_model import OllamaClient
        client = OllamaClient()
        client._available = None
        self.assertFalse(client.is_available())

    def test_hybrid_ai_client_init(self):
        from modules.ai.local_model import HybridAIClient
        client = HybridAIClient(config={"ai_strategy": "cloud_first"})
        self.assertEqual(client.strategy, "cloud_first")

    def test_hybrid_current_backend_unavailable(self):
        from modules.ai.local_model import HybridAIClient
        client = HybridAIClient(config={})
        client._cloud = MagicMock(available=False)
        client._local = MagicMock(is_available=lambda: False)
        self.assertEqual(client.current_backend(), "unavailable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
