from django.urls import path
from .views import notification_list, notification_detail, mark_all_read

urlpatterns = [
    path("", notification_list, name="notification-list"),
    path("<int:pk>/", notification_detail, name="notification-detail"),
    path("mark-all-read/", mark_all_read, name="notification-mark-all-read"),
]
