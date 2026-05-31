"""Tests - NLP v2 (résolution pronominale + entités étendues)"""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestIntentClassifierV2(unittest.TestCase):

    def setUp(self):
        from modules.nlp.intent_classifier import IntentClassifier
        self.clf = IntentClassifier()

    def test_weather_intent(self):
        intent, _ = self.clf.classify("quelle est la météo à Paris")
        self.assertEqual(intent, "GET_WEATHER")

    def test_open_app_intent(self):
        intent, _ = self.clf.classify("ouvre Word s'il te plaît")
        self.assertEqual(intent, "OPEN_APPLICATION")

    def test_reminder_intent(self):
        intent, _ = self.clf.classify("rappelle-moi de prendre mes médicaments à 8h")
        self.assertEqual(intent, "SET_REMINDER")

    def test_search_intent(self):
        intent, _ = self.clf.classify("cherche Python sur Google")
        self.assertEqual(intent, "SEARCH_WEB")

    def test_volume_intent(self):
        intent, _ = self.clf.classify("baisse le volume")
        self.assertEqual(intent, "SYSTEM_VOLUME")

    def test_screenshot_intent(self):
        intent, _ = self.clf.classify("fais une capture d'écran")
        self.assertEqual(intent, "TAKE_SCREENSHOT")

    def test_translate_intent(self):
        intent, _ = self.clf.classify("traduis bonjour en anglais")
        self.assertEqual(intent, "TRANSLATE")

    def test_news_intent(self):
        intent, _ = self.clf.classify("donne-moi les actualités")
        self.assertEqual(intent, "GET_NEWS")

    def test_conversation_fallback(self):
        intent, _ = self.clf.classify("comment tu vas aujourd'hui ?")
        self.assertEqual(intent, "CONVERSATION")

    def test_classify_returns_tuple(self):
        result = self.clf.classify("bonjour")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_classify_entities_dict(self):
        _, entities = self.clf.classify("météo demain à Lyon")
        self.assertIsInstance(entities, dict)


class TestPronounResolution(unittest.TestCase):

    def setUp(self):
        from modules.nlp.intent_classifier import IntentClassifier
        self.clf = IntentClassifier()

    def test_enregistre_la(self):
        """'enregistre-la' doit être résolu en référence au document."""
        _, entities = self.clf.classify("enregistre-la maintenant")
        self.assertIn("raw_text", entities)

    def test_ferme_le(self):
        _, entities = self.clf.classify("ferme-le")
        self.assertIn("raw_text", entities)


class TestEntityExtractorV2(unittest.TestCase):

    def setUp(self):
        from modules.nlp.intent_classifier import EntityExtractor
        self.ext = EntityExtractor()

    def test_city_paris(self):
        e = self.ext.extract("météo à Paris", "GET_WEATHER")
        self.assertEqual(e.get("city"), "Paris")

    def test_city_lyon(self):
        e = self.ext.extract("il fait quoi à Lyon", "GET_WEATHER")
        self.assertEqual(e.get("city"), "Lyon")

    def test_time_14h30(self):
        e = self.ext.extract("rappel à 14h30", "SET_REMINDER")
        self.assertEqual(e.get("time"), "14:30")

    def test_time_8h(self):
        e = self.ext.extract("demain à 8h matin", "SET_REMINDER")
        self.assertEqual(e.get("time"), "8:00")

    def test_date_demain(self):
        e = self.ext.extract("réunion demain matin", "SET_REMINDER")
        self.assertEqual(e.get("date"), "demain")

    def test_date_lundi(self):
        e = self.ext.extract("rappel lundi à 9h", "SET_REMINDER")
        self.assertIn("lundi", e.get("date", ""))

    def test_app_word(self):
        e = self.ext.extract("ouvre Word", "OPEN_APPLICATION")
        self.assertEqual(e.get("app"), "word")

    def test_app_chrome(self):
        e = self.ext.extract("lance Chrome", "OPEN_APPLICATION")
        self.assertEqual(e.get("app"), "chrome")

    def test_url_extraction(self):
        e = self.ext.extract("ouvre https://www.google.com", "OPEN_BROWSER")
        self.assertEqual(e.get("url"), "https://www.google.com")

    def test_language_en_anglais(self):
        e = self.ext.extract("traduis bonjour en anglais", "TRANSLATE")
        self.assertIn("anglais", e.get("target_language", "").lower())

    def test_duration_extraction(self):
        e = self.ext.extract("minuterie de 5 minutes", "SET_REMINDER")
        dur = e.get("duration")
        if dur:
            self.assertEqual(dur["value"], 5)

    def test_numbers_extraction(self):
        e = self.ext.extract("volume à 70 pourcent", "SYSTEM_VOLUME")
        nums = e.get("numbers", [])
        self.assertIn(70, nums)

    def test_raw_text_always_present(self):
        e = self.ext.extract("n'importe quoi", "CONVERSATION")
        self.assertIn("raw_text", e)


class TestResponseGeneratorV2(unittest.TestCase):

    def setUp(self):
        from modules.nlp.response_generator import ResponseGenerator
        self.gen = ResponseGenerator

    def test_weather(self):
        r = self.gen.weather("Paris", "ensoleillé", 22.0, 45)
        self.assertIn("Paris", r)
        self.assertIn("22", r)

    def test_reminder_set(self):
        r = self.gen.reminder_set("réunion", "14h30")
        self.assertIn("réunion", r)

    def test_time_response_contains_heure(self):
        r = self.gen.time_response()
        self.assertIn("heure", r.lower())

    def test_date_response_contains_day(self):
        r = self.gen.date_response()
        self.assertIn("nous sommes", r.lower())

    def test_error_response(self):
        r = self.gen.error()
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 5)

    def test_unknown_response(self):
        r = self.gen.unknown()
        self.assertIsInstance(r, str)
        self.assertGreater(len(r), 5)

    def test_list_items_empty(self):
        r = self.gen.list_items("Événements", [])
        self.assertIn("aucun", r.lower())

    def test_list_items_non_empty(self):
        r = self.gen.list_items("Tâches", ["Tâche A", "Tâche B"])
        self.assertIn("Tâche A", r)
        self.assertIn("Tâche B", r)

    def test_greeting_with_name(self):
        r = self.gen.greeting("CHARAMOU", "Alice")
        self.assertIn("CHARAMOU", r)
        self.assertIn("Alice", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
