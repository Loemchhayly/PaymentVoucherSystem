from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    # Voucher CRUD
    path('create/', views.VoucherCreateView.as_view(), name='create'),
    path('<int:pk>/', views.VoucherDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.VoucherEditView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.voucher_delete, name='delete'),

    # Workflow actions
    path('<int:pk>/submit/', views.voucher_submit, name='submit'),
    path('<int:pk>/approve/', views.voucher_approve, name='approve'),

    # Attachments
    path('<int:pk>/upload/', views.upload_attachment, name='upload_attachment'),
    path('<int:pk>/attachments/<int:attachment_id>/', views.download_attachment, name='download_attachment'),

    # PDF Generation
    path('<int:pk>/pdf/', views.voucher_pdf, name='pdf'),
]
