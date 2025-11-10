from django.test import SimpleTestCase

from api.services.lookups import (
    ClubLookupError,
    extract_club_reference,
    normalize_club_lookup,
)


class ClubLookupParserTests(SimpleTestCase):
    def test_extracts_url_from_blob(self):
        raw = "See https://campfire.onelink.me/eBr8?deep_link_sub1=cj1jbHVicyZjPWI2&foo=bar please"
        club_url, club_id = extract_club_reference(raw)
        self.assertEqual(
            club_url,
            "https://campfire.onelink.me/eBr8?deep_link_sub1=cj1jbHVicyZjPWI2&foo=bar",
        )
        self.assertIsNone(club_id)

    def test_extracts_id_from_blob(self):
        club_url, club_id = extract_club_reference(
            "Club ID: b632fc8e-0b41-49de-ade2-21b0cd81db69"
        )
        self.assertIsNone(club_url)
        self.assertEqual(club_id, "b632fc8e-0b41-49de-ade2-21b0cd81db69")

    def test_raises_when_multiple_candidates_present(self):
        with self.assertRaises(ClubLookupError):
            extract_club_reference(
                "https://campfire.onelink.me/abcd?deep_link_sub1=foo "
                "and b632fc8e-0b41-49de-ade2-21b0cd81db69"
            )

    def test_strict_normalization_requires_reference(self):
        with self.assertRaises(ClubLookupError):
            normalize_club_lookup("no useful tokens here", strict=True)

    def test_non_strict_url_fallback(self):
        club_url, club_id = normalize_club_lookup(
            "https://example.com/not-onelink", default_kind="url"
        )
        self.assertEqual(club_url, "https://example.com/not-onelink")
        self.assertIsNone(club_id)

    def test_non_strict_id_fallback(self):
        club_url, club_id = normalize_club_lookup(
            "custom-club-id", default_kind="id"
        )
        self.assertIsNone(club_url)
        self.assertEqual(club_id, "custom-club-id")
