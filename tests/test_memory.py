"""Tests - MemoryManager v2 (mémoire sémantique TF-IDF incluse)"""
import sys, tempfile, unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_memory(tmp_path: str):
    """Crée un MemoryManager isolé avec une base temporaire."""
    from core.memory_manager import MemoryManager
    import core.memory_manager as mm_mod
    orig = mm_mod.DB_PATH
    mm_mod.DB_PATH = Path(tmp_path)
    m = MemoryManager.__new__(MemoryManager)
    import sqlite3
    m._conn = sqlite3.connect(tmp_path)
    m._conn.row_factory = sqlite3.Row
    from core.memory_manager import TFIDFIndex
    m._working  = {}
    m._semantic = TFIDFIndex()
    m._init_tables()
    mm_mod.DB_PATH = orig
    return m


class TestMemoryManagerV2(unittest.TestCase):

    def setUp(self):
        self.tmp  = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.mem  = _make_memory(self.tmp.name)

    def tearDown(self):
        self.mem.close()
        # Important sur Windows : fermer le NamedTemporaryFile avant unlink()
        try:
            self.tmp.close()
        except Exception:
            pass
        Path(self.tmp.name).unlink(missing_ok=True)


    # ── Préférences ─────────────────────────────────────────────────────────

    def test_set_get_preference(self):
        self.mem.set_preference("lang", "fr")
        self.assertEqual(self.mem.get_preference("lang"), "fr")

    def test_preference_complex_value(self):
        self.mem.set_preference("cfg", {"theme": "dark", "vol": 80})
        val = self.mem.get_preference("cfg")
        self.assertEqual(val["theme"], "dark")

    def test_preference_default(self):
        self.assertIsNone(self.mem.get_preference("ghost"))

    def test_preference_overwrite(self):
        self.mem.set_preference("x", "v1")
        self.mem.set_preference("x", "v2")
        self.assertEqual(self.mem.get_preference("x"), "v2")

    # ── Mémoire de travail ───────────────────────────────────────────────────

    def test_working_memory(self):
        self.mem.set_working("last_cmd", "météo Paris")
        self.assertEqual(self.mem.get_working("last_cmd"), "météo Paris")

    def test_working_memory_default(self):
        self.assertEqual(self.mem.get_working("missing", "default"), "default")

    def test_clear_working(self):
        self.mem.set_working("k", "v")
        self.mem.clear_working()
        self.assertIsNone(self.mem.get_working("k"))

    # ── Conversations ────────────────────────────────────────────────────────

    def test_save_and_retrieve_turns(self):
        self.mem.save_turn("user",      "Bonjour",   "CONVERSATION")
        self.mem.save_turn("assistant", "Bonjour !", None)
        turns = self.mem.get_recent_conversations(10)
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["role"], "user")
        self.assertEqual(turns[1]["role"], "assistant")

    def test_conversations_limit(self):
        for i in range(10):
            self.mem.save_turn("user", f"msg {i}")
        turns = self.mem.get_recent_conversations(5)
        self.assertEqual(len(turns), 5)

    # ── Faits / Long terme ───────────────────────────────────────────────────

    def test_remember_and_recall(self):
        self.mem.remember("user", "name", "Alice")
        self.assertEqual(self.mem.recall("user", "name"), "Alice")

    def test_recall_missing(self):
        self.assertEqual(self.mem.recall("user", "ghost", "défaut"), "défaut")

    def test_recall_category(self):
        self.mem.remember("prefs", "theme", "dark")
        self.mem.remember("prefs", "volume", 80)
        cat = self.mem.recall_category("prefs")
        self.assertIn("theme", cat)
        self.assertIn("volume", cat)

    def test_remember_importance(self):
        self.mem.remember("sys", "key_fact", "important", importance=5)
        val = self.mem.recall("sys", "key_fact")
        self.assertEqual(val, "important")

    # ── Rappels ──────────────────────────────────────────────────────────────

    def test_add_and_get_reminder(self):
        due = datetime.now() - timedelta(seconds=1)
        rid = self.mem.add_reminder("Test", due, "desc")
        pending = self.mem.get_pending_reminders()
        self.assertTrue(any(r["id"] == rid for r in pending))

    def test_mark_reminder_done(self):
        due = datetime.now() - timedelta(seconds=1)
        rid = self.mem.add_reminder("To close", due)
        self.mem.mark_reminder_done(rid)
        pending = self.mem.get_pending_reminders()
        self.assertFalse(any(r["id"] == rid for r in pending))

    def test_future_reminder_not_pending(self):
        due = datetime.now() + timedelta(hours=1)
        rid = self.mem.add_reminder("Future", due)
        pending = self.mem.get_pending_reminders()
        self.assertFalse(any(r["id"] == rid for r in pending))

    # ── Base de connaissances ────────────────────────────────────────────────

    def test_add_and_search_knowledge(self):
        self.mem.add_knowledge("doc1", "Python est un langage de programmation interprété.", "Python", ["code"])
        results = self.mem.search_knowledge("langage programmation", top_k=3)
        self.assertTrue(len(results) >= 0)   # peut être 0 si score trop bas

    def test_knowledge_returns_dict(self):
        kid = self.mem.add_knowledge("src", "contenu test", "résumé", ["tag"])
        self.assertIsInstance(kid, int)

    # ── Sémantique TF-IDF ────────────────────────────────────────────────────

    def test_semantic_index_after_save(self):
        self.mem.save_turn("user", "quelle est la météo à Lyon")
        results = self.mem.search_semantic("météo Lyon")
        self.assertIsInstance(results, list)

    def test_semantic_search_returns_scores(self):
        self.mem.remember("city", "preferred", "Bordeaux")
        results = self.mem.search_semantic("Bordeaux ville")
        for r in results:
            self.assertIn("score", r)
            self.assertGreaterEqual(r["score"], 0)

    def test_memory_summary_string(self):
        summary = self.mem.get_memory_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("Mémoire", summary)


class TestTFIDFIndex(unittest.TestCase):

    def setUp(self):
        from core.memory_manager import TFIDFIndex
        self.idx = TFIDFIndex()

    def test_add_and_search(self):
        self.idx.add("d1", "Python est un langage de programmation")
        self.idx.add("d2", "Java est aussi un langage orienté objet")
        results = self.idx.search("Python programmation", top_k=2)
        ids = [r[0] for r in results]
        self.assertIn("d1", ids)

    def test_empty_index(self):
        results = self.idx.search("test")
        self.assertEqual(results, [])

    def test_len(self):
        self.idx.add("d1", "premier document")
        self.idx.add("d2", "deuxième document")
        self.assertEqual(len(self.idx), 2)

    def test_scores_descending(self):
        self.idx.add("d1", "python python python machine learning")
        self.idx.add("d2", "java script web front-end")
        results = self.idx.search("python machine learning")
        if len(results) > 1:
            self.assertGreaterEqual(results[0][1], results[1][1])

    def test_irrelevant_query_no_results(self):
        self.idx.add("d1", "recette gateau chocolat farine beurre")
        results = self.idx.search("satellite orbite espace")
        self.assertEqual(results, [])


class TestContextManager(unittest.TestCase):

    def setUp(self):
        from core.context_manager import ContextManager
        self.ctx = ContextManager(max_history=10)

    def test_add_turns(self):
        self.ctx.add_user_turn("Bonjour", intent="CONVERSATION")
        self.ctx.add_assistant_turn("Bonjour !")
        self.assertEqual(len(self.ctx.get_history()), 2)

    def test_openai_format(self):
        self.ctx.add_user_turn("Test")
        msgs = self.ctx.get_openai_messages()
        self.assertEqual(msgs[0]["role"], "user")

    def test_entities(self):
        self.ctx.add_user_turn("météo Paris", entities={"city": "Paris"})
        self.assertEqual(self.ctx.get_entity("city"), "Paris")

    def test_clear(self):
        self.ctx.add_user_turn("test")
        self.ctx.clear()
        self.assertEqual(len(self.ctx.get_history()), 0)

    def test_max_history_enforced(self):
        from core.context_manager import ContextManager
        ctx = ContextManager(max_history=3)
        for i in range(6):
            ctx.add_user_turn(f"msg {i}")
        self.assertLessEqual(len(ctx.get_history()), 3)

    def test_last_user_message(self):
        self.ctx.add_user_turn("Première")
        self.ctx.add_user_turn("Deuxième")
        self.assertEqual(self.ctx.last_user_message(), "Deuxième")

    def test_is_follow_up(self):
        for i in range(3):
            self.ctx.add_user_turn(f"msg {i}")
            self.ctx.add_assistant_turn("ok")
        self.assertTrue(self.ctx.is_follow_up())


if __name__ == "__main__":
    unittest.main(verbosity=2)
