# The `ports_in_region()` function returns a table containing all `ports.code` belong to certain region
raw__ports_in_region = """CREATE OR REPLACE function ports_in_region(slugName text) returns TABLE(code text) AS $$
WITH RECURSIVE cte AS (
    select slug, name, parent_slug from regions where slug = slugName
    UNION
    select r.slug, r.name, r.parent_slug from regions as r INNER JOIN cte ON r.parent_slug = cte.slug
)
select code from ports INNER JOIN cte ON ports.parent_slug = cte.slug
$$ LANGUAGE SQL;"""
