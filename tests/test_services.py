"""
Tests - Services externes
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestWeatherService(unittest.TestCase):

    @patch('modules.services.weather_service.requests.get')
    def test_get_weather_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "name": "Paris",
            "sys": {"country": "FR"},
            "weather": [{"description": "ensoleillé", "icon": "01d"}],
            "main": {"temp": 22.0, "feels_like": 20.0, "humidity": 50},
            "wind": {"speed": 3.5}
        }
        mock_get.return_value.raise_for_status = MagicMock()

        import os
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
            from modules.services.weather_service import WeatherService
            svc = WeatherService()
            data = svc.get_weather("Paris")

        self.assertEqual(data["city"], "Paris")
        self.assertEqual(data["temp"], 22.0)
        self.assertEqual(data["description"], "ensoleillé")

    def test_handle_no_api_key(self):
        import os
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENWEATHER_API_KEY", None)
            from modules.services.weather_service import WeatherService
            svc = WeatherService()
            svc.api_key = ""
            result = svc.handle(entities={"city": "Lyon"})
        self.assertIn("Désolé", result)

    @patch('modules.services.weather_service.requests.get')
    def test_handle_with_city_entity(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "name": "Lyon",
            "sys": {"country": "FR"},
            "weather": [{"description": "nuageux", "icon": "02d"}],
            "main": {"temp": 18.0, "feels_like": 17.0, "humidity": 65},
            "wind": {"speed": 2.0}
        }
        mock_get.return_value.raise_for_status = MagicMock()

        import os
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "test_key"}):
            from importlib import reload
            import modules.services.weather_service as ws
            reload(ws)
            svc = ws.WeatherService()
            result = svc.handle(entities={"city": "Lyon"})

        self.assertIn("Lyon", result)


class TestReminderService(unittest.TestCase):

    def _make_service(self):
        from modules.services.reminder_service import ReminderService
        mock_scheduler = MagicMock()
        mock_memory = MagicMock()
        mock_memory.add_reminder.return_value = 1
        return ReminderService(scheduler=mock_scheduler, memory=mock_memory)

    def test_handle_with_time(self):
        svc = self._make_service()
        result = svc.handle(entities={
            "raw_text": "rappelle-moi la réunion",
            "time": "14:30",
            "date": None
        })
        self.assertIn("Rappel", result)

    def test_handle_no_time(self):
        svc = self._make_service()
        result = svc.handle(entities={
            "raw_text": "rappelle-moi quelque chose",
            "time": None,
            "date": None
        })
        self.assertIn("heure", result.lower())

    def test_extract_title(self):
        svc = self._make_service()
        title = svc._extract_title("rappelle-moi de prendre mes médicaments")
        self.assertNotIn("rappelle", title.lower())

    def test_parse_datetime_demain(self):
        svc = self._make_service()
        result = svc._parse_datetime("demain", "10:00")
        self.assertIsNotNone(result)
        tomorrow = datetime.now() + timedelta(days=1)
        self.assertEqual(result.date(), tomorrow.date())


class TestSearchService(unittest.TestCase):

    @patch('modules.services.search_service.requests.get')
    def test_search_returns_results(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "Heading": "Python",
            "AbstractText": "Python est un langage de programmation.",
            "AbstractURL": "https://python.org",
            "RelatedTopics": []
        }
        mock_get.return_value.raise_for_status = MagicMock()

        from modules.services.search_service import SearchService
        svc = SearchService()
        results = svc.search("Python")
        self.assertTrue(len(results) > 0)
        self.assertIn("Python", results[0]["snippet"])

    @patch('modules.services.search_service.webbrowser.open')
    def test_handle_opens_browser_on_no_results(self, mock_browser):
        with patch('modules.services.search_service.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "AbstractText": "",
                "RelatedTopics": []
            }
            mock_get.return_value.raise_for_status = MagicMock()

            from modules.services.search_service import SearchService
            svc = SearchService()
            result = svc.handle(entities={"raw_text": "cherche Python"})

        self.assertIn("navigateur", result.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
