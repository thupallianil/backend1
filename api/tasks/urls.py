from django.urls import path
from .views import task_list_create, task_detail, task_add_comment

urlpatterns = [
    path("", task_list_create, name="task-list-create"),
    path("<int:pk>/", task_detail, name="task-detail"),
    path("<int:pk>/comments/", task_add_comment, name="task-add-comment"),
]
