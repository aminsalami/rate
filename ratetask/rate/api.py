from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from rate.models import Price
from rate.serializers import RatesListSerializer, RatesListValidator


class RatesAPI(GenericAPIView):
    CODE_LEN = 5
    serializer_class = RatesListSerializer
    queryset = Price.objects.first()

    def get(self, request, *args, **kwargs):
        # validate the query params using the serializer
        params = self.validate_qparams(request.query_params)

        # NOTE: The task requirements does not specify how exactly a CODE is distinguished with slug.
        # Nevertheless, we assumed that slug is always more than 5 chars.
        if len(params["origin"]) > self.CODE_LEN and len(params["destination"]) > self.CODE_LEN:
            query = self.region2region(params)
        elif len(params["origin"]) > self.CODE_LEN:
            query = self.region2port(params)
        elif len(params["destination"]) > self.CODE_LEN:
            query = self.port2region(params)
        else:
            query = self.port2port(params)

        data = self.serializer_class(query, many=True).data
        return Response(data={"results": data}, status=200)

    def validate_qparams(self, qparams: dict) -> dict:
        v = RatesListValidator(data=qparams)
        v.is_valid(raise_exception=True)
        return v.validated_data

    def port2port(self, params: dict):
        """
        return a django_query representing the average price between two ports.
        """
        q = """
            WITH cte as (
                SELECT 1 as id, count(price) as c, day, CASE WHEN count(price) >= 3 THEN round(avg(price)) ELSE null END as average_price
                FROM prices    
                WHERE orig_code = %s and dest_code = %s
                GROUP BY day
            )
            SELECT 1 as id, c, generated_day, average_price
            FROM cte RIGHT OUTER JOIN (
                select generated_day::date from generate_series(%s::date, %s::date, '1 day'::interval) as generated_day
            ) as s ON cte.day = s.generated_day
            ORDER BY generated_day
        """
        result = Price.objects.raw(
            q,
            params=(params["origin"], params["destination"], params["date_from"], params["date_to"])
        )
        return result

    def port2region(self, p: dict):
        """
        return a django query representing the average prices from `origin port` to all ports in `destination` region
        """
        q = """
        WITH RECURSIVE cte AS (
            select slug, name, parent_slug from regions where slug = %(slug)s
            UNION
            select r.slug, r.name, r.parent_slug from regions as r INNER JOIN cte ON r.parent_slug = cte.slug
        ),
        destination_ports as (
            select code from ports as p INNER JOIN cte ON p.parent_slug = cte.slug
        ),
        result as (
            SELECT count(price) as c, day, CASE WHEN count(price) >= 3 THEN avg(price)::integer ELSE null END as average_price
            FROM prices
            JOIN destination_ports ON dest_code = destination_ports.code
            WHERE orig_code = %(origin)s
            GROUP BY day
            ORDER BY day
        )
        select 1 as id, c, average_price, generated_day FROM result
        RIGHT OUTER JOIN (
            select generated_day::date from generate_series(%(from)s::date, %(to)s::date, '1 day'::interval) as generated_day
        ) as s ON generated_day = day        
        """
        return Price.objects.raw(
            q,
            params={"slug": p["destination"], "origin": p["origin"], "from": p["date_from"], "to": p["date_to"]}
        )

    def region2port(self, p: dict):
        """
        generate a query when:
            - origin parameter is a `region slug`
            - destination parameter is a `port code`
        """
        q = """
        WITH RECURSIVE cte AS (
            select slug, name, parent_slug from regions where slug = %(slug)s
            UNION
            select r.slug, r.name, r.parent_slug from regions as r INNER JOIN cte ON r.parent_slug = cte.slug
        ),
        origin_ports as (
            select code from ports as p INNER JOIN cte ON p.parent_slug = cte.slug
        ),
        result as (
            SELECT count(price) as c, day, CASE WHEN count(price) >= 3 THEN avg(price)::integer ELSE null END as average_price
            FROM prices
            JOIN origin_ports ON orig_code = origin_ports.code
            WHERE dest_code = %(dest)s
            GROUP BY day
            ORDER BY day
        )
        select 1 as id, c, average_price, generated_day FROM result
        RIGHT OUTER JOIN (
            select generated_day::date from generate_series(%(from)s::date, %(to)s::date, '1 day'::interval) as generated_day
        ) as s ON generated_day = day        
                """
        return Price.objects.raw(
            q,
            params={"slug": p["origin"], "dest": p["destination"], "from": p["date_from"], "to": p["date_to"]}
        )

    def region2region(self, p: dict):
        """
        """
        q = """
        WITH RECURSIVE cte1 AS (
            select slug, name, parent_slug from regions where slug = %(origin_slug)s
            UNION
            select r.slug, r.name, r.parent_slug from regions as r INNER JOIN cte1 ON r.parent_slug = cte1.slug
        ),
        origin_ports as (
            select code from ports as p INNER JOIN cte1 ON p.parent_slug = cte1.slug
        ),
        cte2 AS (
            select slug, name, parent_slug from regions where slug = %(dest_slug)s
            UNION
            select r.slug, r.name, r.parent_slug from regions as r INNER JOIN cte2 ON r.parent_slug = cte2.slug
        ),
        destination_ports as (
            select code from ports as p INNER JOIN cte2 ON p.parent_slug = cte2.slug
        ),
        result as (
            SELECT count(price) as c, day, CASE WHEN count(price) >= 3 THEN round(avg(price))::integer ELSE null END as average_price
            FROM prices
            JOIN origin_ports ON prices.orig_code = origin_ports.code
            JOIN destination_ports ON prices.dest_code = destination_ports.code
            GROUP BY day
            ORDER BY day
        )
        select 1 as id, c, average_price, generated_day FROM result
        RIGHT OUTER JOIN (
            select generated_day::date from generate_series(%(from)s::date, %(to)s::date, '1 day'::interval) as generated_day
        ) as s ON generated_day = day;
        """
        return Price.objects.raw(
            q,
            params={"origin_slug": p["origin"], "dest_slug": p["destination"], "from": p["date_from"],
                    "to": p["date_to"]}
        )
