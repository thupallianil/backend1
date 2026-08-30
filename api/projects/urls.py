from django.urls import path
from .views import (
    project_list_create,
    project_detail,
    project_assign_vendor,
    project_remove_vendor,
    project_stats,
)

urlpatterns = [
    path("", project_list_create, name="project-list-create"),
    path("stats/", project_stats, name="project-stats"),
    path("<int:pk>/", project_detail, name="project-detail"),
    path("<int:pk>/assign-vendor/", project_assign_vendor, name="project-assign-vendor"),
    path("<int:pk>/remove-vendor/<int:vendor_id>/", project_remove_vendor, name="project-remove-vendor"),
]
