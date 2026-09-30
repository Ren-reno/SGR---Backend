from django.urls import path

from .views import activity, evidence

app_name = 'performance'

urlpatterns = [
    path('activities/', activity.ActivityListView.as_view(), name='activity_list'),
    path('activities/new/', activity.ActivityCreateView.as_view(), name='activity_create'),
    path('activities/<int:pk>/edit/', activity.ActivityUpdateView.as_view(), name='activity_update'),
    path('evidences/', evidence.EvidenceListView.as_view(), name='evidence_list'),
    path('evidences/new/', evidence.EvidenceCreateView.as_view(), name='evidence_create'),
    # Evidence usa su código (texto) como clave primaria. Se usa `path` y no
    # `str` porque el Admin permite códigos con cualquier carácter, "/"
    # incluido, y con `str` un solo código así haría fallar el listado entero
    # (NoReverseMatch al armar el enlace "Editar").
    path('evidences/<path:pk>/edit/', evidence.EvidenceUpdateView.as_view(), name='evidence_update'),
]
