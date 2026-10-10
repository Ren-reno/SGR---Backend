from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import ActivityViewSet, CommitmentViewSet

app_name = 'api'

router = DefaultRouter()
router.register('activities', ActivityViewSet, basename='activity')
router.register('commitments', CommitmentViewSet, basename='commitment')

urlpatterns = [
    # POST {"username", "password"} -> {"access", "refresh"}
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # POST {"refresh"} -> {"access"}
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls