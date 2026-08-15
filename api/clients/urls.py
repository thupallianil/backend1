from django.urls import path
from .views import client_list_create, client_detail, client_portal_credentials

urlpatterns = [
    path("", client_list_create, name="client-list-create"),
    path("<int:pk>/", client_detail, name="client-detail"),
    path("<int:pk>/credentials/", client_portal_credentials, name="client-portal-credentials"),
]
