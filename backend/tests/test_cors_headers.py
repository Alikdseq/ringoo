"""CORS preflight: кастомные заголовки SPA не должны блокироваться браузером."""

from django.test import TestCase


class CorsAllowHeadersTest(TestCase):
    def test_preflight_allows_x_auth_cookies(self):
        response = self.client.options(
            "/api/v1/auth/token/refresh/",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-auth-cookies,content-type",
        )
        self.assertIn(response.status_code, (200, 204))
        allowed = (response.get("Access-Control-Allow-Headers") or "").lower()
        self.assertIn("x-auth-cookies", allowed)
