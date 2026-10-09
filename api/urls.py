from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = 'api'

urlpatterns = [
    # POST {"username", "password"} -> {"access", "refresh"}
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # POST {"refresh"} -> {"access"}
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
