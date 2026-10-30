"""Тесты HTTP-клиента 1С и регистрации партнёра (только моки, без реального сервера)."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import UserProfile
from integrations.onec.client import OneCClient, OneCClientError
from integrations.onec.importer import (
    ImportMode,
    apply_catalog_import,
    plan_catalog_import_from_xml_strings,
)
from integrations.onec.parser import BASE_FOLDER_CODE, OneCParseError, parse_folders_xml
from integrations.onec.registration import register_user_in_onec

User = get_user_model()

FOLDERS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ПапкиНоменклатуры>
  <Папка code="00-00010097" parentCode="" name="База"/>
  <Папка code="00-00010100" parentCode="" name="Телефоны"/>
  <Папка code="00-00010101" parentCode="00-00010100" name="Apple"/>
</ПапкиНоменклатуры>
"""

PRODUCTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Товары>
  <Товар code="00-00000126" parentCode="00-00010101" name="iPhone Test"
    type="Телефоны" typeID="t1"
    sklad="Магазин А" skladID="wh-a" series="" seriesID=""
    quantity="2.000" price="10 000.00"/>
  <Товар code="00-00000126" parentCode="00-00010101" name="iPhone Test"
    type="Телефоны" typeID="t1"
    sklad="Магазин Б" skladID="wh-b" series="" seriesID=""
    quantity="0" price="10 000.00"/>
  <Товар code="00-00000127" parentCode="00-00010101" name="iPhone Empty Qty"
    type="Телефоны" typeID="t1"
    sklad="Магазин А" skladID="wh-a" series="" seriesID=""
    quantity="" price="5 000.00"/>
  <Товар code="00-00000128" parentCode="00-00010101" name="iPhone No Wh"
    type="Телефоны" typeID="t1"
    sklad="" skladID="" series="" seriesID=""
    quantity="" price="1 000.00"/>
</Товары>
"""

ENGLISH_FOLDERS = """<?xml version="1.0" encoding="UTF-8"?>
<folders>
  <folder code="00-00010100" parentCode="" name="Phones"/>
</folders>
"""


class _FakeHTTPResponse:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "application/xml"):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self, n: int = -1):
        if n is None or n < 0:
            return self._body
        return self._body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class OneCHttpClientTests(TestCase):
    def test_disabled_by_default(self):
        client = OneCClient(enabled=False, base_url="http://localhost/razrab/hs")
        with self.assertRaises(OneCClientError):
            client.fetch_folders_xml()

    def test_build_url(self):
        client = OneCClient(enabled=False, base_url="http://localhost/razrab/hs")
        self.assertTrue(
            client.build_url("CatalogFolders/folders").endswith("CatalogFolders/folders")
        )

    def test_fetch_folders_success_and_basic_auth(self):
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="site_user",
            password="secret",
            timeout=5,
        )
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["accept"] = req.headers.get("Accept")
            captured["auth"] = req.headers.get("Authorization")
            return _FakeHTTPResponse(FOLDERS_XML.encode("utf-8"))

        with patch.object(OneCClient, "_http_open", side_effect=fake_urlopen):
            xml = client.fetch_folders_xml()

        self.assertIn("Папка", xml)
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["accept"], "application/xml")
        self.assertTrue(captured["auth"].startswith("Basic "))
        self.assertNotIn("secret", captured["auth"])  # base64, not plaintext in assert sense
        # пароль не должен попасть в plaintext заголовок кроме base64
        self.assertNotIn("secret", str(captured))

    def test_fetch_products_success(self):
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )

        with patch.object(
            OneCClient,
            "_http_open",
            return_value=_FakeHTTPResponse(PRODUCTS_XML.encode("utf-8")),
        ):
            xml = client.fetch_products_xml()
        self.assertIn("Товар", xml)

    def test_http_401(self):
        import urllib.error

        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )

        err = urllib.error.HTTPError(
            "http://example.test/x", 401, "Unauthorized", hdrs=None, fp=io.BytesIO(b"deny")
        )
        with patch.object(OneCClient, "_http_open", side_effect=err):
            with self.assertRaises(OneCClientError) as ctx:
                client.fetch_folders_xml()
        self.assertEqual(ctx.exception.status_code, 401)

    def test_http_404_405_500(self):
        import urllib.error

        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )
        for code in (404, 405, 500):
            err = urllib.error.HTTPError(
                "http://example.test/x", code, "err", hdrs=None, fp=io.BytesIO(b"x")
            )
            with patch.object(OneCClient, "_http_open", side_effect=err):
                with self.assertRaises(OneCClientError) as ctx:
                    client.fetch_products_xml()
            self.assertEqual(ctx.exception.status_code, code)

    def test_timeout(self):
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )
        with patch.object(OneCClient, "_http_open", side_effect=TimeoutError()):
            with self.assertRaises(OneCClientError) as ctx:
                client.fetch_folders_xml()
        self.assertIsNone(ctx.exception.status_code)
        self.assertIn("Тайм-аут", str(ctx.exception))

    def test_xxe_dtd_rejected(self):
        evil = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            "<ПапкиНоменклатуры><Папка code='1' parentCode='' name='&xxe;'/></ПапкиНоменклатуры>"
        )
        with self.assertRaises(OneCParseError):
            parse_folders_xml(evil)

    def test_invalid_xml_does_not_write(self):
        from apps.products.models import Category, Product

        before_c = Category.objects.count()
        before_p = Product.objects.count()
        with self.assertRaises(OneCParseError):
            plan_catalog_import_from_xml_strings(
                "not-xml<<<",
                PRODUCTS_XML,
                mode=ImportMode.DRY_RUN,
            )
        self.assertEqual(Category.objects.count(), before_c)
        self.assertEqual(Product.objects.count(), before_p)

    def test_empty_xml_rejected(self):
        with self.assertRaises(OneCParseError):
            plan_catalog_import_from_xml_strings(
                "<?xml version='1.0'?><root/>",
                "<?xml version='1.0'?><root/>",
                mode=ImportMode.DRY_RUN,
            )


class OneCParserHttpShapeTests(TestCase):
    def test_excludes_base_folder(self):
        folders = parse_folders_xml(FOLDERS_XML)
        codes = {f.code for f in folders}
        self.assertNotIn(BASE_FOLDER_CODE, codes)
        self.assertIn("00-00010100", codes)

    def test_english_folder_tags(self):
        folders = parse_folders_xml(ENGLISH_FOLDERS)
        self.assertEqual(folders[0].code, "00-00010100")

    def test_duplicate_folder_codes_flagged(self):
        xml = """<?xml version="1.0"?><ПапкиНоменклатуры>
          <Папка code="00-1" parentCode="" name="A"/>
          <Папка code="00-1" parentCode="" name="B"/>
        </ПапкиНоменклатуры>"""
        products = """<?xml version="1.0"?><Товары>
          <Товар code="p1" parentCode="00-1" name="X" type="" typeID=""
            sklad="" skladID="" series="" seriesID="" quantity="" price="100"/>
        </Товары>"""
        plan = plan_catalog_import_from_xml_strings(xml, products, mode=ImportMode.DRY_RUN)
        self.assertIn("folder_duplicate_code", {i["type"] for i in plan.issues})

    def test_multi_warehouse_one_card_zero_vs_empty(self):
        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_XML, PRODUCTS_XML, mode=ImportMode.DRY_RUN
        )
        codes = [p.onec_code for p in plan.products]
        self.assertEqual(codes.count("00-00000126"), 1)
        stocks_126 = [s for s in plan.stocks if s.onec_code == "00-00000126"]
        statuses = {s.sklad_id: s.quantity_status for s in stocks_126 if s.action == "upsert"}
        self.assertEqual(statuses.get("wh-a"), "positive")
        self.assertEqual(statuses.get("wh-b"), "explicit_zero")
        empty_qty = next(s for s in plan.stocks if s.onec_code == "00-00000127")
        self.assertEqual(empty_qty.quantity_status, "missing")
        self.assertEqual(empty_qty.action, "skip")

    def test_apply_from_valid_xml(self):
        from apps.products.models import Category, Product

        plan = plan_catalog_import_from_xml_strings(
            FOLDERS_XML, PRODUCTS_XML, mode=ImportMode.APPLY
        )
        result = apply_catalog_import(plan)
        self.assertGreater(result["categories"], 0)
        self.assertTrue(Product.objects.filter(onec_code="00-00000126").exists())
        self.assertTrue(Category.objects.filter(onec_code="00-00010100").exists())


class OneCRegistrationTests(TestCase):
    def _user(self, **kwargs):
        user = User.objects.create_user(
            phone=kwargs.pop("phone", "79001112233"),
            password="pass12345",
            **kwargs,
        )
        UserProfile.objects.create(
            user=user,
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
        )
        return user

    def test_saves_partner_id(self):
        user = self._user()
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )
        body = json.dumps(
            {"ClientId": "7d29c3b4-7d95-4e25-9dd9-4cb35c236b7c", "created": True}
        ).encode()

        with patch.object(
            OneCClient,
            "_http_open",
            return_value=_FakeHTTPResponse(
                body, status=201, content_type="application/json"
            ),
        ):
            result = register_user_in_onec(user, client=client)

        user.refresh_from_db()
        self.assertEqual(result.partner_id, "7d29c3b4-7d95-4e25-9dd9-4cb35c236b7c")
        self.assertEqual(user.onec_partner_id, result.partner_id)
        self.assertEqual(user.onec_partner_status, User.ONEC_PARTNER_SYNCED)

    def test_saves_legacy_partner_id_alias(self):
        user = self._user(phone="79001112236")
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )
        body = json.dumps(
            {"partnerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "created": False}
        ).encode()
        with patch.object(
            OneCClient,
            "_http_open",
            return_value=_FakeHTTPResponse(
                body, status=200, content_type="application/json"
            ),
        ):
            result = register_user_in_onec(user, client=client)
        user.refresh_from_db()
        self.assertEqual(user.onec_partner_id, result.partner_id)

    def test_skip_when_partner_id_exists(self):
        user = self._user(phone="79001112234")
        user.onec_partner_id = "already-there"
        user.onec_partner_status = User.ONEC_PARTNER_SYNCED
        user.save()
        client = MagicMock()
        result = register_user_in_onec(user, client=client)
        self.assertTrue(result.skipped)
        client.register_partner.assert_not_called()

    def test_timeout_marks_pending_review_no_retry(self):
        user = self._user(phone="79001112235")
        client = OneCClient(
            enabled=True,
            base_url="http://example.test/razrab/hs",
            username="u",
            password="p",
        )
        with patch.object(OneCClient, "_http_open", side_effect=TimeoutError()):
            result = register_user_in_onec(user, client=client)
        user.refresh_from_db()
        self.assertEqual(result.status, User.ONEC_PARTNER_PENDING_REVIEW)
        self.assertEqual(user.onec_partner_status, User.ONEC_PARTNER_PENDING_REVIEW)
        self.assertIsNone(user.onec_partner_id)

        # повтор без force не шлёт POST
        client2 = MagicMock()
        again = register_user_in_onec(user, client=client2)
        self.assertTrue(again.skipped)
        client2.register_partner.assert_not_called()
