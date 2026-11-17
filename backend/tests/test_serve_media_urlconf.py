"""
SERVE_MEDIA + DEBUG=False must register /media/<path> (Docker prod via Next proxy).
"""

from importlib import reload
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import clear_url_caches, set_urlconf


class ServeMediaUrlconfTests(TestCase):
    def tearDown(self):
        clear_url_caches()
        set_urlconf(None)
        import config.urls as urls_mod

        reload(urls_mod)
        set_urlconf(settings.ROOT_URLCONF)
        super().tearDown()

    def _reload_urls(self):
        clear_url_caches()
        import config.urls as urls_mod

        reload(urls_mod)
        set_urlconf(urls_mod)
        return urls_mod

    @override_settings(DEBUG=False, SERVE_MEDIA=True)
    def test_media_route_serves_existing_file(self):
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        rel = Path("products/2026/11")
        (media_root / rel).mkdir(parents=True, exist_ok=True)
        target = media_root / rel / "serve_media_probe.jpg"
        payload = b"\xff\xd8\xff\xd9"  # minimal JPEG marker pair
        target.write_bytes(payload)

        self._reload_urls()
        client = Client()
        resp = client.get(f"/media/{rel.as_posix()}/serve_media_probe.jpg")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), payload)
        self.assertIn("image", (resp.get("Content-Type") or "").lower())

    @override_settings(DEBUG=False, SERVE_MEDIA=False)
    def test_media_route_absent_without_flag(self):
        self._reload_urls()
        client = Client()
        resp = client.get("/media/products/2026/11/missing.jpg")
        self.assertEqual(resp.status_code, 404)
