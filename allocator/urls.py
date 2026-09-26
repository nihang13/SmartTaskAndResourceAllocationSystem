from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('my-tasks/', views.my_tasks, name='my_tasks'),

    path('tasks/', views.task_list, name='task_list'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('tasks/<int:pk>/complete/', views.mark_task_completed, name='task_complete'),
    path('tasks/export/csv/', views.export_tasks_csv, name='export_tasks_csv'),

    path('allocate/', views.trigger_auto_allocation, name='trigger_allocation'),

    path('team/', views.user_profiles, name='user_profiles'),
    path('team/<int:pk>/edit/', views.profile_edit, name='profile_edit'),
    path('team/<int:pk>/toggle-availability/', views.toggle_availability, name='toggle_availability'),

    path('logs/', views.allocation_logs, name='allocation_logs'),
    path('logs/export/csv/', views.export_allocation_logs_csv, name='export_logs_csv'),
]
