# Xeneta Rate Task

### How to run?
Start the services using the docker-compose file:
`[sudo] docker compose up --build`

It will start 3 containers (pg, app, nginx). `nginx` will be listening on port 80 on host machine.
Connect to the pg instance on port 5433 (default user/pass is defined in env.env file):
`PGPASSWORD=xeneta psql -h 127.0.0.1 -U xeneta -p 5433`

Finally, find the rate api on **`http://127.0.0.1/v1/rates`**

### Run tests

`[sudo] docker compose exec app python manage.py test`

### Some notes
* Due to django not being able to work with tables without primary_key (in this case, `prices` table), I added a custom.sql to add an id column as pk on container startup.
* The task requirements do not specify how exactly a port.code is distinguished with slug. slug could potentially be a 5-letter word that results in conflict. I assumed slug len is _always_ more than 5.
* volume is used to make pgData persistence for my own convenience
* The first version of raw queries I used in RatesAPI class had many boilerplate. All of them were using a CTE to retrieve the ports in a geographic region.
Thus I thought It's a good idea to add a SQL-function for that purpose to make the less boilerplate/simpler (check the migrations/0002_*.py file).
