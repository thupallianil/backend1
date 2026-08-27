from django.urls import path
from .views import vendor_list_create, vendor_detail, vendor_stats

urlpatterns = [
    path("", vendor_list_create, name="vendor-list-create"),
    path("stats/", vendor_stats, name="vendor-stats"),
    path("<int:pk>/", vendor_detail, name="vendor-detail"),
]
