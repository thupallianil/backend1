from django.urls import path
from .views import (
    deliverable_list_create,
    deliverable_detail,
    deliverable_admin_review,
    deliverable_client_review,
)

urlpatterns = [
    path("", deliverable_list_create, name="deliverable-list-create"),
    path("<int:pk>/", deliverable_detail, name="deliverable-detail"),
    path("<int:pk>/admin-review/", deliverable_admin_review, name="deliverable-admin-review"),
    path("<int:pk>/client-review/", deliverable_client_review, name="deliverable-client-review"),
]
