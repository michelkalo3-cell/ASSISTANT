"""Tests - Agents spécialisés"""
import sys, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWebAgent(unittest.TestCase):

    def setUp(self):
        from core.agents.web_agent import WebAgent
        self.agent = WebAgent(engine=None)

    def test_can_handle_cherche(self):
        self.assertTrue(self.agent.can_handle("cherche Python", {}))

    def test_can_handle_google(self):
        self.assertTrue(self.agent.can_handle("google les actualités", {}))

    def test_cannot_handle_unrelated(self):
        self.assertFalse(self.agent.can_handle("allume la lumière", {}))

    @patch('core.agents.web_agent.WebAgent._search')
    def test_execute_with_results(self, mock_search):
        mock_search.return_value = [
            {"title": "Python", "snippet": "Python est un langage.", "url": "https://python.org"}
        ]
        result = self.agent.execute("cherche Python", {"raw_text": "Python"})
        self.assertIn("Python", result)

    @patch('core.agents.web_agent.WebAgent._search')
    @patch('core.agents.web_agent.WebAgent._open_browser')
    def test_execute_no_results_opens_browser(self, mock_browser, mock_search):
        mock_search.return_value = []
        result = self.agent.execute("cherche xyz123", {"raw_text": "xyz123"})
        mock_browser.assert_called_once()
        self.assertIn("navigateur", result.lower())

    def test_steps_logged(self):
        with patch.object(self.agent, '_search', return_value=[]):
            with patch.object(self.agent, '_open_browser'):
                self.agent.execute("cherche test", {"raw_text": "test"})
        self.assertTrue(len(self.agent.get_steps()) > 0)


class TestWordAgent(unittest.TestCase):

    def setUp(self):
        from core.agents.word_agent import WordAgent
        self.agent = WordAgent(engine=None)

    def test_can_handle_word(self):
        self.assertTrue(self.agent.can_handle("ouvre Word", {}))

    def test_can_handle_document(self):
        self.assertTrue(self.agent.can_handle("crée un document", {}))

    def test_can_handle_lettre(self):
        self.assertTrue(self.agent.can_handle("rédige une lettre", {}))

    def test_cannot_handle_weather(self):
        self.assertFalse(self.agent.can_handle("météo Paris", {}))

    def test_extract_title_sur(self):
        title = self.agent._extract_title("crée un document sur le projet")
        self.assertIn("Projet", title)

    def test_extract_title_default(self):
        title = self.agent._extract_title("ouvre word")
        self.assertEqual(title, "Document CHARAMOU")

    @patch('core.agents.word_agent.WordAgent._create_document')
    def test_execute_create_routes_correctly(self, mock_create):
        mock_create.return_value = "Document créé."
        result = self.agent.execute("crée un document rapport", {}, None)
        mock_create.assert_called_once()
        self.assertEqual(result, "Document créé.")


class TestSystemAgent(unittest.TestCase):

    def setUp(self):
        from core.agents.system_agent import SystemAgent
        self.agent = SystemAgent(engine=None)

    def test_can_handle_volume(self):
        self.assertTrue(self.agent.can_handle("monte le volume", {}))

    def test_can_handle_capture(self):
        self.assertTrue(self.agent.can_handle("capture d'écran", {}))

    def test_can_handle_cpu(self):
        self.assertTrue(self.agent.can_handle("quel est le cpu", {}))

    def test_cannot_handle_weather(self):
        self.assertFalse(self.agent.can_handle("météo Lyon", {}))

    @patch('psutil.cpu_percent', return_value=42.0)
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.sensors_battery', return_value=None)
    def test_get_system_stats(self, mock_bat, mock_disk, mock_ram, mock_cpu):
        mock_ram.return_value = MagicMock(percent=60.0, used=4e9, total=8e9)
        mock_disk.return_value = MagicMock(percent=45.0)
        result = self.agent._get_system_stats()
        self.assertIn("42", result)
        self.assertIn("60", result)


class TestBaseAgent(unittest.TestCase):

    def test_base_agent_abstract(self):
        from core.agents.base_agent import BaseAgent
        with self.assertRaises(TypeError):
            BaseAgent()

    def test_concrete_agent_steps(self):
        from core.agents.web_agent import WebAgent
        agent = WebAgent(engine=None)
        agent._log_step("Étape 1")
        agent._log_step("Étape 2")
        steps = agent.get_steps()
        self.assertEqual(len(steps), 2)
        self.assertIn("Étape 1", steps)


class TestKnowledgeManager(unittest.TestCase):

    def setUp(self):
        import tempfile
        from core.memory_manager import MemoryManager
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        # Mémoire isolée
        import sqlite3
        from core.memory_manager import TFIDFIndex
        self.mem = MemoryManager.__new__(MemoryManager)
        self.mem._conn = sqlite3.connect(self.tmp.name)
        self.mem._conn.row_factory = sqlite3.Row
        self.mem._working  = {}
        self.mem._semantic = TFIDFIndex()
        self.mem._init_tables()

        from modules.services.knowledge_manager import KnowledgeManager
        self.km = KnowledgeManager(memory=self.mem, ai_client=None)

    def tearDown(self):
        self.mem.close()
        # Important sur Windows : fermer le NamedTemporaryFile avant unlink()
        try:
            self.tmp.close()
        except Exception:
            pass
        Path(self.tmp.name).unlink(missing_ok=True)


    def test_ingest_text(self):
        result = self.km.ingest_text("Python est un langage populaire.", source="test")
        self.assertEqual(result["source"], "test")
        self.assertGreater(result["chunks"], 0)

    def test_chunk_text(self):
        long_text = "mot " * 300
        chunks = self.km._chunk(long_text)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), self.km.CHUNK_SIZE + 10)

    def test_search_after_ingest(self):
        self.km.ingest_text("Django est un framework Python pour le web.", source="django")
        results = self.km.search("framework web Python")
        self.assertIsInstance(results, list)

    def test_query_without_ai_returns_string(self):
        self.km.ingest_text("Machine learning est un domaine de l'IA.", source="ml")
        result = self.km.query("intelligence artificielle machine learning")
        self.assertIsInstance(result, str)

    def test_handle_no_query(self):
        result = self.km.handle(entities={})
        self.assertIn("souhaitez", result.lower())

    def test_ingest_url_error_handled(self):
        result = self.km.ingest_url("https://url-inexistante-charamou.xyz/page")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
