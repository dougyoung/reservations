# Simple Reservation Service

```bash
# source env/bin/activate
```

## Throttling

There is a global 1/sec request rate throttle across all resources and actions. This is set lower than it would most
likely need to be in production, but serves for demonstrative purposes. Other resources and/or action combinations may
have additional throttling constraints, please see each resource and action's description for more details.

## Resources

### Reservations

`GET /reservations`

`GET /reservations/<id>`

`POST /reservations`

`PUT /reservations<id>`

This resource and action combination has a specific throttling policy wherein any PUT containing `status` will be subject
to a throttling rate of 1/minute.

`PATCH /reservations/<id>`

This resource and action combination has a specific throttling policy wherein any PUT containing `status` will be subject
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