from django.core.cache import cache as default_cache
from rest_framework.throttling import SimpleRateThrottle

cache = default_cache


class ReservationStatusRateThrottle(SimpleRateThrottle):
    scope = 'reservation_status'
    rate = '1/min'

    def allow_request(self, request, view):
        # If this request involves the status in the request payload.
        if 'status' in request.data:
            # Then use this specific policy.
            return super(ReservationStatusRateThrottle, self).allow_request(request, view)
        else:
            return True

    # Set cache key equal to this throttle's scope plus the request path.
    # This ensures that the throttle applies across all requests to this resource,
    # instead of a per-user basis. Note that this does not include any query parameters.
    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.path
        }