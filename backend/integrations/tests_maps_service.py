"""
Unit-тесты для integrations.maps_service (задача 2.4.3).
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.stores.models import Store

from integrations.maps_service import (
    _validate_yandex_geocode_response,
    distance_km,
    geocode_address,
    geocode_and_nearest_stores,
    get_nearest_stores,
)


class TestValidateYandexGeocodeResponse(TestCase):
    def test_rejects_non_dict(self):
        self.assertFalse(_validate_yandex_geocode_response(None))
        self.assertFalse(_validate_yandex_geocode_response([]))

    def test_rejects_error_status(self):
        self.assertFalse(_validate_yandex_geocode_response({"status": "error"}))

    def test_rejects_non_dict_response(self):
        self.assertFalse(
            _validate_yandex_geocode_response({"response": "bad"}),
        )

    def test_rejects_missing_collection(self):
        self.assertFalse(_validate_yandex_geocode_response({"response": {}}))

    def test_rejects_non_dict_collection(self):
        self.assertFalse(
            _validate_yandex_geocode_response(
                {"response": {"GeoObjectCollection": []}},
            ),
        )

    def test_accepts_minimal_valid_shape(self):
        self.assertTrue(
            _validate_yandex_geocode_response(
                {"response": {"GeoObjectCollection": {}}},
            ),
        )


class TestGeocodeAddress(TestCase):
    def test_empty_address_returns_none(self):
        self.assertIsNone(geocode_address(""))
        self.assertIsNone(geocode_address(None))

    @patch("integrations.maps_service._request_geocode")
    def test_returns_coords_on_success(self, mock_request):
        mock_request.return_value = {
            "response": {
                "GeoObjectCollection": {
                    "featureMember": [
                        {
                            "GeoObject": {
                                "Point": {"pos": "37.617644 55.755826"},
                            },
                        },
                    ],
                },
            },
        }
        result = geocode_address("Москва")
        self.assertIsNotNone(result)
        lat, lon = result
        self.assertAlmostEqual(lat, 55.755826)
        self.assertAlmostEqual(lon, 37.617644)
        mock_request.assert_called_once_with("Москва")

    @patch("integrations.maps_service._request_geocode")
    def test_returns_none_when_no_results(self, mock_request):
        mock_request.return_value = {
            "response": {
                "GeoObjectCollection": {
                    "featureMember": [],
                },
            },
        }
        self.assertIsNone(geocode_address("unknown place"))

    @patch("integrations.maps_service._request_geocode")
    def test_returns_none_on_api_error(self, mock_request):
        mock_request.return_value = None
        self.assertIsNone(geocode_address("Москва"))

    @patch("integrations.maps_service._request_geocode")
    def test_returns_none_on_malformed_response(self, mock_request):
        mock_request.return_value = {"response": {}}
        self.assertIsNone(geocode_address("Москва"))


class TestDistanceKm(TestCase):
    def test_distance_same_point_is_zero(self):
        self.assertAlmostEqual(distance_km(55.75, 37.61, 55.75, 37.61), 0.0, places=2)

    def test_distance_moscow_to_spb_rough(self):
        # Москва ~ 55.75, 37.61; СПб ~ 59.93, 30.31; ~634 км
        d = distance_km(55.755826, 37.617644, 59.934280, 30.335099)
        self.assertGreater(d, 600)
        self.assertLess(d, 700)


class TestGetNearestStores(TestCase):
    def setUp(self):
        self.store1 = Store.objects.create(
            name="Магазин 1",
            slug="store-1",
            address="ул. Ленина 1",
            city="Москва",
            latitude=Decimal("55.755826"),
            longitude=Decimal("37.617644"),
        )
        self.store2 = Store.objects.create(
            name="Магазин 2",
            slug="store-2",
            address="ул. Пушкина 2",
            city="Москва",
            latitude=Decimal("55.760000"),
            longitude=Decimal("37.620000"),
        )
        self.store3 = Store.objects.create(
            name="Без координат",
            slug="store-no-coords",
            address="ул. Неизвестная",
            city="Город",
            latitude=None,
            longitude=None,
        )

    def test_returns_stores_sorted_by_distance(self):
        # Точка рядом с store1
        results = get_nearest_stores(55.755826, 37.617644, limit=5)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["store"].slug, "store-1")
        self.assertLess(results[0]["distance_km"], results[1]["distance_km"])

    def test_respects_limit(self):
        results = get_nearest_stores(55.755826, 37.617644, limit=1)
        self.assertEqual(len(results), 1)

    def test_excludes_stores_without_coords(self):
        results = get_nearest_stores(55.755826, 37.617644, limit=10)
        slugs = [r["store"].slug for r in results]
        self.assertNotIn("store-no-coords", slugs)

    def test_only_active_when_requested(self):
        self.store2.is_active = False
        self.store2.save()
        results = get_nearest_stores(55.755826, 37.617644, limit=10, only_active=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["store"].slug, "store-1")


class TestGeocodeAndNearestStores(TestCase):
    @patch("integrations.maps_service.geocode_address")
    def test_returns_none_and_empty_when_geocode_fails(self, mock_geocode):
        mock_geocode.return_value = None
        coords, stores = geocode_and_nearest_stores("Несуществующий адрес")
        self.assertIsNone(coords)
        self.assertEqual(stores, [])

    @patch("integrations.maps_service.geocode_address")
    def test_returns_coords_and_stores_when_geocode_succeeds(self, mock_geocode):
        mock_geocode.return_value = (55.755826, 37.617644)
        Store.objects.create(
            name="М",
            slug="m",
            address="А",
            city="Москва",
            latitude=Decimal("55.755826"),
            longitude=Decimal("37.617644"),
        )
        coords, stores = geocode_and_nearest_stores("Москва", limit=5)
        self.assertIsNotNone(coords)
        self.assertEqual(coords[0], 55.755826)
        self.assertEqual(coords[1], 37.617644)
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["store"].slug, "m")
