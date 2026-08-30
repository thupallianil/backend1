from django.urls import path
from .views import client_dashboard, client_projects_list, client_approvals_list

urlpatterns = [
    path("dashboard/", client_dashboard, name="client-portal-dashboard"),
    path("projects/", client_projects_list, name="client-portal-projects"),
    path("approvals/", client_approvals_list, name="client-portal-approvals"),
]
