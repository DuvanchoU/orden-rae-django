# dashboard/urls.py
from django.urls import path
from .views import DashboardView, logout_view 

app_name = 'dashboard' 

urlpatterns = [
    # Dashboard home
    path('', DashboardView.as_view(), name='dashboard_home'),
    path('logout/', logout_view, name='logout'),
]