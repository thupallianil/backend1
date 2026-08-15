from django.urls import path
from .views import client_list_create, client_detail

urlpatterns = [
    path("", client_list_create, name="client-list-create"),
    path("<int:pk>/", client_detail, name="client-detail"),
]
