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
    path('my-drafts/', views.MyDraftsView.as_view(), name='my_drafts'),
    path('all-vouchers/', views.AllVouchersView.as_view(), name='all_vouchers'),
    path('bulk-submit-drafts/', views.bulk_submit_drafts, name='bulk_submit_drafts'),
    path('search/', views.dashboard_search, name='dashboard_search'),
]
