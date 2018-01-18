# Simple Reservation Service

This is a simple Reservation application to provide service around Reservations for hotels and other establishments that
allow booking of rooms.

## Requirements

To run locally you will require Python 3. This has been tested with Python 3.6.2.

## Run locally

Pull repository from Github:

```bash
# git clone git@github.com:dougyoung/reservations.git
```

Activate your virtualenv:

```bash
# cd reservations
# source env/bin/activate
```

Install pip dependencies:

```bash
# pip3 install -r requirements.txt
```

_Simple Reservation Service_ utilizes materialized views to denormalize Reservation, Guest, and Room data into a single
cached table. In order to generate these views please run:

```bash
# python3 manage.py sync_pgviews
```

## Throttling

There is a global 1/sec request rate throttle across all resources and actions. This is set lower than it would most
likely need to be in production, but serves for demonstrative purposes. Other resources and/or action combinations may
have additional throttling constraints, please see each resource and action's description for more details.

## Resources

### Guests

`GET /guests`

`GET /guests/<id>`

`POST /guests`

`PUT /guests/<id>`

`PATCH /guest/<id>`

`DELETE /guest/<id>`

### Reservations

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

`GET /rooms`

`GET /rooms/<id>`

`POST /rooms`

`PUT /rooms/<id>`

`PATCH /rooms/<id>`

`DELETE /rooms/<id>`

Currently DELETE on Rooms is *not supported*. The business logic for how to handle Reservations for such a rare scenario
would first need to be thought through carefully.