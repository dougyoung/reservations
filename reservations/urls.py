from django.conf.urls import url, include
from rest_framework import routers
from reservations.api import views

router = routers.DefaultRouter()
router.register(r'reservations', views.ReservationViewSet)
router.register(r'rooms', views.RoomViewSet)

# Setup a router that does not require trailing slash
slashless_router = routers.DefaultRouter(trailing_slash=False)
slashless_router.registry = router.registry[:]

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^', include(slashless_router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
