# Simple Reservation Service

This is a simple Reservation application to provide service around Reservations for hotels and other establishments that
allow booking of rooms. This repository represents a first iteration of such a service, as many more considerations
need to be made to bring it to production-readiness.

## Running

For both the Docker version and for running locally the first step is the same. Pull this repository from Github:

```bash
git clone git@github.com:dougyoung/reservations.git
```

### Docker

To run the application using Docker, follow these steps:

1. Have `docker` installed.
2. Be in the root directory, which contains docker-compose.yml.
3. Docker up the containers: `docker-compose up`
4. Run migrations: `docker-compose run api python3 manage.py migrate`

_Simple Reservation Service_ utilizes materialized views to denormalize Reservation, Guest, and Room data into a single
cached table. In order to generate these views please run:

```bash
docker-compose run api python3 manage.py sync_pgviews
```

### Local

To run locally you will require Python 3. This has been tested with Python 3.6.2. Also have [virtualenv](https://virtualenv.pypa.io/en/stable/installation)
installed, as well as Postgres 9.6.3.

1. Change directory to `src`: `cd src`
2. Make virtualenv folder: `virtualenv .env`
3. Activate your virtualenv: `source .env/bin/activate`
4. Install pip dependencies: `pip3 install -r requirements.txt`

_Simple Reservation Service_ utilizes materialized views to denormalize Reservation, Guest, and Room data into a single
cached table. In order to generate these views please run:

```bash
python3 manage.py sync_pgviews
```

Next create a database and a database user. Note you should have Postgres installed locally 

1. `psql`
2. `CREATE DATABASE reservation_api;`
3. `CREATE USER reservation_api_user;'
4. `ALTER USER reservation_api_user CREATEDB;`

Now you can migrate the database:

```
python3 manage.py migrate
```

Finally, run the server:

```
python3 manage.py runserver
```

## Choice of database

Since Reservations are atomic in nature and also must be _highly_ available. They are transactional atomic as a 
Room must be both available and reserved without a single transaction, and a Room must never belong to two
simultaneous Reservations for any given period of time of the Reservation. They must also be _highly_
available as any interruption or latency in interruption would be unacceptable to the client. For these
reasons I have chosen [Postgres](https://www.postgresql.org/) as the datastore as it provides both of these attributes. In order to 
maximize availability Reservations are denormalized into a [materialized view](https://www.postgresql.org/docs/9.3/static/sql-creatematerializedview.html).
Refreshes to this materialized view happen concurrently, so that simultaneous reads are not blocked. This
has the advantage of retaining the high availability of the information, while entaining eventual consistency
of the information. We also then cache CurrentAndUpcoming Reservations in Redis to offer even lower latency
by keeping the information in memory. We could achieve some of this functionality this with an embedded
document in something like MongoDB, but it is semantically incorrect to embed Rooms inside Reservations, as
Reservations are ephemeral while Rooms are persistent.

## Tests

### Docker

To run tests in the Docker container perform the following command:

```bash
docker-compose run api python3 manage.py test
```

### Local

To run tests locally perform this command:

```bash
python3 manage.py test
```

## Throttling

There is a global 1/sec request rate throttle across all resources and actions. This is set lower than it would most
likely need to be in production, but serves for demonstrative purposes. Other resources and/or action combinations may
have additional throttling constraints, please see each resource and action's description for more details.

## Resources

### Guests

Each Guest action takes or responds with the following JSON attributes:

`first_name`: The primary name of a Guest.
`last_name`: The secondary name of a Guest.

`GET /guests`

`GET /guests/<id>`

`POST /guests`

`PUT /guests/<id>`

`PATCH /guest/<id>`

`DELETE /guest/<id>`

### Reservations

`in_date`: The first date in which a Guest has reserved a room.
`out_date`: The last date in which a Guest has reserved a room.
`status`: The current state of the Reservation: `PENDING`, `CHECKED-IN`, `CHECKED-OUT`.
`checkin_datetime`: The date and time which a Guest checked-in to their Reservation. Not settable.
`checkout_datetime`: The date and time which a Guest checked-out of their Reservation. Not settable.
`guest`: The primary key of the Guest which holds the reservation.
`room`: The primary key of the Room which holds the reservation.

`GET /reservations`

`GET /reservations/<id>`

`POST /reservations`

`PUT /reservations<id>`

A PUT request to a Reservation has a specific throttling policy wherein any PUT containing `status` will be subject
to a throttling rate of 1/minute.

`PATCH /reservations/<id>`

A PATCH request to a Reservation has a specific throttling policy wherein any PATCH containing `status` will be subject
to a throttling rate of 1/minute.

`DELETE /reservations/<id>`

### Rooms

Each Room action takes or responsds with the following JSON attributes:

`number`: A String representing the colloquial Room identifier.

`GET /rooms`

`GET /rooms/<id>`

`POST /rooms`

`PUT /rooms/<id>`

`PATCH /rooms/<id>`

`DELETE /rooms/<id>`

Currently DELETE on Rooms is *not supported*. The business logic for how to handle Reservations for such a rare scenario
would first need to be thought through carefully.

## Tests

To run tests in the Docker container perform the following command:

```
docker-compose run api python3 manage.py test
```

## Next steps

There are many more things I would like to do to improve this service further. They are, in no particular order:

1. Better authentication for clients
    1. Perhaps token-based authentication.
2. Pagination for list actions
3. Validations:
    1. One Room can only belong to one Reservation between arrival and departure dates.
    2. Reservation in_date should be before or on out_date.
    3. Make sure checkin_datetime is on or after in_date.
    4. Make sure checkout_datetime is on or after out_date.
    5. Ensure Reservation state transitions only move in a logical direction.
4. Handle deletion of Rooms
    1. Would need to talk with business partners about ramifications to Reservations in such an unlikely event.
5. Inject secrets at deploy time (e.g. SECRET_KEY)
6. Deleting a Reservation should soft-delete the Reservation
    1. This would allow a Reservation to be potentially restored later.
    2. This would persist interesting guest behavior for later analysis, such as insights into reducing cancellations.
7. Materialized view refresh would perform even better as a Postgres trigger.
8. More data modeling: e.g. Hotels, Employees, Location, RoomAvailability, RoomType, and many others.
    1. This would also help us potentially shard Reservations into more targeted segments.
    2. Hotel would have many Rooms, many Employees, and many Locations.
    3. This would help reduce the load of refreshing the CurrentAndUpcomingReservation materialized view as a concurrent refresh
       could select only Reservations which are updated for a given Hotel.
    4. RoomAvailability should update transitionally with Reservation creation & update.
9. Reservations
    1. Should have a one-to-many relationship with Rooms as a Reservation may be for 1 or more rooms.
    2. Expected check-in date and expected check-out date are currently immutable from the API to avoid complexity 
       with Room availability. This functionality should be implemented.
10. CurrentAndUpcomingReservations
    1. Should be refreshed by a cron job at least once per day, per Hotel Location.
    2. Depending on the business use case this should possibly be two different resources, CurrentReservations and
       UpcomingReservations, as each of these resources may serve a separate business function.
11. Models/Serializers/Views should be split up for easier maintenance.
12. Database access should be locked down more.
