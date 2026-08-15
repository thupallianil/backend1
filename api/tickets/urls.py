from django.urls import path
from .views import ticket_list, ticket_detail, ticket_reply

urlpatterns = [
    path("", ticket_list, name="ticket-list"),
    path("<int:pk>/", ticket_detail, name="ticket-detail"),
    path("<int:pk>/reply/", ticket_reply, name="ticket-reply"),
]
