import random
from datetime import date, timedelta

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
        self.r1 = Region.objects.create(slug="region-1", name="region #1", parent=None)
        self.r11 = Region.objects.create(slug="region-1-1", name="region #1-1", parent=self.r1)
        self.p_10001 = Port.objects.create(code="10001", name="port-10001", parent=self.r1)
        self.p_11001 = Port.objects.create(code="11001", name="port-11001", parent=self.r11)
        self.p_11002 = Port.objects.create(code="11002", name="port-11002", parent=self.r11)
        self.region1_ports = [self.p_10001, self.p_11001, self.p_11002]
        # ----------- Region-2 ---------------
        self.r2 = Region.objects.create(slug="region-2", name="region #2", parent=None)
        self.p_20001 = Port.objects.create(code="20001", name="port-20001", parent=self.r2)
        self.p_20002 = Port.objects.create(code="20002", name="port-20002", parent=self.r2)
        self.region2_ports = [self.p_20001, self.p_20002]

        # Generate random prices for random ports (from region-1 >> to region-2) and vice versa
        for i in range(200):
            Price.objects.create(
                orig_code=random.choice(self.region1_ports + self.region2_ports),
                dest_code=random.choice(self.region1_ports + self.region2_ports),
                day=random.choice(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06"]),
                price=i
            )

    def test_port_not_found(self):
        resp = self.api.get(path="/v1/rates/", data=self.sample_qp)
        self.assertEqual(resp.status_code, 404)

    def test_region_not_found(self):
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

        # Assert the first day is correct. postgres avg()::integer automatically rounds the number
        q = Price.objects.filter(orig_code=d["origin"], dest_code=d["destination"], day=d["date_from"]) \
            .values_list("price", flat=True)
        if len(q) < 3:
            self.assertIsNone(resp.data["results"][0]["average_price"])
        else:
            expected = round(sum(q) / len(q))
            self.assertEqual(expected, resp.data["results"][0]["average_price"])
        # Assert the last day is correct. postgres avg()::integer automatically rounds the number
        q2 = Price.objects.filter(orig_code=d["origin"], dest_code=d["destination"], day=d["date_to"]) \
            .values_list("price", flat=True)
        if len(q2) < 3:
            self.assertIsNone(resp.data["results"][-1]["average_price"])
        else:
            expected = round(sum(q2) / len(q2))
            self.assertEqual(expected, resp.data["results"][-1]["average_price"])

    def test_port2port_when_some_days_have_no_prices(self):
        """
        We want to make sure that from 2023-01-01 to 2023-01-09 there are exactly 9 day slots that
        some of them are json_null.
        """
        Price.objects.filter(day="2023-01-01", orig_code=self.p_10001).delete()
        Price.objects.filter(day="2023-01-06", dest_code=self.p_20001).delete()
        d = {
            "date_from": "2023-01-01", "date_to": "2023-01-06",
            "origin": self.p_10001.code, "destination": self.p_20001.code
        }
        resp = self.api.get(path="/v1/rates/", data=d)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], "application/json")
        self.assertEqual(6, len(resp.data["results"]))
        # We have deleted all the prices where orig_code is 10001 on the first day
        self.assertIsNone(resp.data["results"][0]["average_price"])
        self.assertIsNone(resp.data["results"][-1]["average_price"])

    def test_port2region(self):
        """
        Test if all ports which belongs to `destination region and its children` are included in the avg calculation
        """
        d = {
            "date_from": "2023-01-01", "date_to": "2023-01-06",
            "origin": self.p_20001.code, "destination": self.r1.slug
        }
        resp = self.api.get(path="/v1/rates/", data=d)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(6, len(resp.data["results"]))
        self.assertEqual(resp.data["results"][0]["day"], "2023-01-01")

        # ports which are in region-1: two of them are children
        q = Price.objects.filter(
            orig_code=d["origin"], dest_code__in=self.region1_ports, day="2023-01-01"
        ).values_list("price", flat=True)
        if len(q) < 3:
            self.assertIsNone(resp.data["results"][0]["average_price"])
        else:
            expected = round(sum(q) / len(q))
            self.assertEqual(resp.data["results"][0]["average_price"], expected)

    def test_region2port(self):
        """
        Test if all ports belongs to `region-1` are included in the avg calculation
        """
        d = {
            "date_from": "2023-01-01", "date_to": "2023-01-05",
            "origin": self.r1.slug, "destination": self.p_20002.code
        }
        resp = self.api.get(path="/v1/rates/", data=d)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(5, len(resp.data["results"]))

        # get prices for ports belong to region-1
        q = Price.objects.filter(
            orig_code__in=self.region1_ports, dest_code=d["destination"], day="2023-01-05"
        ).values_list("price", flat=True)
        if len(q) < 3:
            self.assertIsNone(resp.data["results"][-1]["average_price"])
        else:
            expected = round(sum(q) / len(q))
            self.assertEqual(resp.data["results"][-1]["average_price"], expected)

        # Add a new parent to r1, test with depth=3
        r0 = Region.objects.create(slug="region-0", name="region #0", parent=None)
        self.r1.parent = r0
        self.r1.save()
        Price.objects.create(orig_code=self.p_11002, dest_code=self.p_20002, day="2023-01-05", price=6000)
        # Test again
        resp = self.api.get(path="/v1/rates/", data=dict(d, **{"origin": r0.slug}))
        self.assertEqual(resp.status_code, 200)
        q = q.all()
        if len(q) < 3:
            self.assertIsNone(resp.data["results"][-1]["average_price"])
        else:
            expected = round(sum(q) / len(q))
            self.assertEqual(resp.data["results"][-1]["average_price"], expected)

    def test_region2region(self):
        """
        Test if the avg value is calculated correctly between two regions with children.
        origin region is `region-2` and destination region is `region-1`
        """
        d = {
            "date_from": "2023-01-01", "date_to": "2023-01-05",
            "origin": self.r2.slug, "destination": self.r1.slug
        }
        resp = self.api.get(path="/v1/rates/", data=d)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(5, len(resp.data["results"]))
        # validate
        region1_ports = [self.p_10001, self.p_11001, self.p_11002]
        region2_ports = [self.p_20001, self.p_20002]

        for idx, day in enumerate([date(2023, 1, 1) + timedelta(days=i) for i in range(5)]):
            q = Price.objects.filter(
                orig_code__in=region2_ports,
                dest_code__in=region1_ports,
                day=day
            ).values_list("price", flat=True)
            if len(q) < 3:
                self.assertIsNone(resp.data["results"][idx]["average_price"])
            else:
                expected = round(sum(q) / len(q))
                self.assertFalse(abs(resp.data["results"][idx]["average_price"] - expected) > 1)
