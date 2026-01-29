from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='home'),
    path('pending/', views.PendingActionView.as_view(), name='pending'),
    path('in-progress/', views.InProgressView.as_view(), name='in_progress'),
    path('approved/', views.ApprovedView.as_view(), name='approved'),
    path('cancelled/', views.CancelledView.as_view(), name='cancelled'),
    path('my-vouchers/', views.MyVouchersView.as_view(), name='my_vouchers'),
]
