from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    ActivityViewSet,
    CommitmentViewSet,
    MetaViewSet,
    PeriodViewSet,
)
from .views_operational import EvidenceViewSet, ValidationViewSet

app_name = 'api'

router = DefaultRouter()
router.register('activities', ActivityViewSet, basename='activity')
router.register('commitments', CommitmentViewSet, basename='commitment')
router.register('metas', MetaViewSet, basename='meta')
router.register('periods', PeriodViewSet, basename='period')
router.register('evidence', EvidenceViewSet, basename='evidence')
router.register('validations', ValidationViewSet, basename='validation')

urlpatterns = [
    # POST {"username", "password"} -> {"access", "refresh"}
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    # POST {"refresh"} -> {"access"}
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls