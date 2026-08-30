from django.urls import path
from .views import message_list_create, mark_messages_read

urlpatterns = [
    path("", message_list_create, name="message-list-create"),
    path("mark-read/", mark_messages_read, name="message-mark-read"),
]
