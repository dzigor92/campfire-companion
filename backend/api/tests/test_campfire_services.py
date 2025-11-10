from unittest.mock import patch

from django.test import SimpleTestCase

import api.services.campfire as campfire_services


class CampfireTokenProviderTests(SimpleTestCase):
    def setUp(self):
        campfire_services.default_token_provider.cache_clear()
        campfire_services.get_campfire_config.cache_clear()

    @patch.object(campfire_services, "_cached_env_token", return_value="env-token")
    def test_env_token_provider_returns_cached_value(self, mock_env):
        provider = campfire_services.env_token_provider()
        self.assertEqual(provider(), "env-token")
        self.assertEqual(provider(), "env-token")
        mock_env.assert_called_once()

    @patch.object(campfire_services, "_cached_env_token", return_value=None)
    @patch.object(campfire_services, "_get_database_token", side_effect=["db-token", None])
    @patch.object(campfire_services.logger, "warning")
    def test_chained_provider_falls_back_to_db(self, mock_warning, mock_db, _mock_env):
        provider = campfire_services.chained_token_provider(
            ("env", campfire_services.env_token_provider()),
            ("database", campfire_services.database_token_provider()),
        )
        self.assertEqual(provider(), "db-token")
        self.assertIsNone(provider())
        mock_db.assert_any_call()
        mock_warning.assert_called_once()
