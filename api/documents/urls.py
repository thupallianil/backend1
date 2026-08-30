from django.urls import path
from .views import document_list_create, document_detail

urlpatterns = [
    path("", document_list_create, name="document-list-create"),
    path("<int:pk>/", document_detail, name="document-detail"),
]
