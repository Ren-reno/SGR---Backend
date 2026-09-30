from django.urls import path

from .views import activity, commitment, evidence, home, validation

app_name = 'performance'

urlpatterns = [
    path('', home.HomeView.as_view(), name='home'),
    path('activities/', activity.ActivityListView.as_view(), name='activity_list'),
    path('activities/new/', activity.ActivityCreateView.as_view(), name='activity_create'),
    path('activities/<int:pk>/edit/', activity.ActivityUpdateView.as_view(), name='activity_update'),
    path('activities/<int:pk>/delete/', activity.ActivityDeleteView.as_view(), name='activity_delete'),
    path('evidences/', evidence.EvidenceListView.as_view(), name='evidence_list'),
    path('evidences/new/', evidence.EvidenceCreateView.as_view(), name='evidence_create'),
    # Evidence usa su código (texto) como clave primaria. Se usa `path` y no
    # `str` porque el Admin permite códigos con cualquier carácter, "/"
    # incluido, y con `str` un solo código así haría fallar el listado entero
    # (NoReverseMatch al armar el enlace "Editar").
    path('evidences/<path:pk>/edit/', evidence.EvidenceUpdateView.as_view(), name='evidence_update'),
    path('evidences/<path:pk>/delete/', evidence.EvidenceDeleteView.as_view(), name='evidence_delete'),
    path('validations/', validation.ValidationListView.as_view(), name='validation_list'),
    path('validations/new/', validation.ValidationCreateView.as_view(), name='validation_create'),
    path('validations/<int:pk>/edit/', validation.ValidationUpdateView.as_view(), name='validation_update'),
    path('validations/<int:pk>/delete/', validation.ValidationDeleteView.as_view(), name='validation_delete'),
    path('commitments/', commitment.CommitmentListView.as_view(), name='commitment_list'),
    path('commitments/new/', commitment.CommitmentCreateView.as_view(), name='commitment_create'),
    path('commitments/<int:pk>/edit/', commitment.CommitmentUpdateView.as_view(), name='commitment_update'),
    path('commitments/<int:pk>/delete/', commitment.CommitmentDeleteView.as_view(), name='commitment_delete'),
]
