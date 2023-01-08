import random

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from rate.api import RatesAPI
from rate.models import Region, Port, Price


class TestRatesQueryParams(TestCase):
    """Test the query_params validation on `v1/rates` api"""

    def setUp(self) -> None:
        self.sample_qp = {
            "date_from": "2023-01-01", "date_to": "2023-01-03", "origin": "GG1DD", "destination": "ABCDE",
        }

    def test_params_are_required(self):
        """test validation fails when at least one of `date_from, date_to, origin, destination` is not provided"""
        rates_api = RatesAPI()
        for key, _ in self.sample_qp.items():
            qp = self.sample_qp.copy()
            qp.pop(key)
            with self.assertRaises(ValidationError):
                rates_api.validate_qparams(qp)

    # def test_validate_date_format(self):
    #     """the v1/rates/ API only accept date as `YYYY-MM-DD`"""
    #     ratesAPI = RatesAPI()
    #     qp = self.sample_qp.copy()
    #     qp.update({"date_from": "2010-1-1"})
    #     self.assertRaises(ratesAPI.validate_rates_qparams(qp))

    def test_origin_or_dest_len(self):
        """test the origin & destination codes are at least 5 characters"""
        rates_api = RatesAPI()
        qp = self.sample_qp.copy()
        qp.update({"origin": "aaaa"})
        with self.assertRaises(ValidationError):
            rates_api.validate_qparams(qp)

        qp.update({"destination": "A"})
        with self.assertRaises(ValidationError):
            rates_api.validate_qparams(qp)


class TestRatesAveragePrice(APITestCase):
    """test if /v1/rates works fine with different combinations of (port, region)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api = cls.client_class()
        cls.sample_qp = {
            "date_from": "2023-01-01", "date_to": "2023-01-03", "origin": "GG1DD", "destination": "ABCDE",
        }

    def setUp(self) -> None:
        # ----------- Region-1 ---------------
        r1 = Region.objects.create(slug="region-1", name="region #1", parent=None)
        r11 = Region.objects.create(slug="region-1-1", name="region #1-1", parent=r1)
        self.p_10001 = Port.objects.create(code="10001", name="port-10001", parent=r1)
        p_11001 = Port.objects.create(code="11001", name="port-11001", parent=r11)
        p_11002 = Port.objects.create(code="11002", name="port-11002", parent=r11)

        # ----------- Region-2 -------p_11001--------
        r2 = Region.objects.create(slug="region-2", name="region #2", parent=None)
        self.p_20001 = Port.objects.create(code="20001", name="port-20001", parent=r2)
        self.p_20002 = Port.objects.create(code="20002", name="port-20002", parent=r2)

        # Generate random prices for random ports (from region-1 >> to region-2)
        for i in range(100):
            Price.objects.create(
                orig_code=random.choice([self.p_10001, p_11001, p_11002]),
                dest_code=random.choice([self.p_20001, self.p_20002]),
                day=random.choice(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06"]),
                price=i
            )

    def test_port_not_found(self):
        resp = self.api.get(path="/v1/rates/", data=self.sample_qp)
        self.assertEqual(resp.status_code, 404)

    def test_port2port_prices(self):
        """test if average price is valid when origin is a port & destination is also a port"""
        d = {
            "date_from": "2023-01-01", "date_to": "2023-01-02",
            "origin": self.p_10001.code, "destination": self.p_20001.code
        }
        resp = self.api.get(path="/v1/rates/", data=d)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], "application/json")
        # Expected exactly 2 price_average, because of the (date_from, date_to)
        self.assertEqual(2, len(resp.data.get("results")))

        q = Price.objects.filter(orig_code=d["origin"], dest_code=d["destination"], day=d["date_from"]) \
            .values_list("price", flat=True)
        expected = int(sum(q) / len(q))
        if len(q) >= 3:
            self.assertEqual(expected, resp.data["results"][0]["average_price"])
        else:
            self.assertIsNone(expected, resp.data["results"][0]["average_price"])

        q2 = Price.objects.filter(orig_code=d["origin"], dest_code=d["destination"], day=d["date_to"]) \
            .values_list("price", flat=True)
        expected = int(sum(q2) / len(q2))
        if len(q2) >= 3:
            self.assertEqual(expected, resp.data["results"][0]["average_price"])
        else:
            self.assertIsNone(expected, resp.data["results"][0]["average_price"])

    def test_port2port_when_some_days_have_no_prices(self):
        """
        We want to make sure that from 2023-01-01 to 2023-01-09 there are exactly 9 day slots that
        some of them are json_null.
        """
        pass

    def test_port2region(self):
        pass

    def test_region2region(self):
        pass

    def test_average_for_root_region_is_equal_to_all_children(self):
        """
        The average price for a region should be exactly the same as the average price for all of its children.
        Meaning that for `region-1 >> p_20002`, the average price should be equal to `p_10001 + p_11001 + p_11002 > p_20002`
        """
        pass

    def test_price_is_null(self):
        pass
