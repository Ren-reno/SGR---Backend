from django.urls import path

from .views import activity

app_name = 'performance'

urlpatterns = [
    path('activities/', activity.ActivityListView.as_view(), name='activity_list'),
    path('activities/new/', activity.ActivityCreateView.as_view(), name='activity_create'),
    path('activities/<int:pk>/edit/', activity.ActivityUpdateView.as_view(), name='activity_update'),
]
