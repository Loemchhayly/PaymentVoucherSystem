from django.urls import path
from . import views

app_name = 'vouchers'

urlpatterns = [
    # Payment Voucher (PV) CRUD
    path('pv/create/', views.VoucherCreateView.as_view(), name='create'),
    path('pv/<int:pk>/', views.VoucherDetailView.as_view(), name='detail'),
    path('pv/<int:pk>/edit/', views.VoucherEditView.as_view(), name='edit'),
    path('pv/<int:pk>/delete/', views.voucher_delete, name='delete'),
    path('pv/<int:pk>/repeat/', views.voucher_repeat, name='repeat'),

    # PV Workflow actions
    path('pv/<int:pk>/submit/', views.voucher_submit, name='submit'),
    path('pv/<int:pk>/approve/', views.voucher_approve, name='approve'),

    # PV Attachments
    path('pv/<int:pk>/upload/', views.upload_attachment, name='upload_attachment'),
    path('pv/<int:pk>/attachments/<int:attachment_id>/', views.download_attachment, name='download_attachment'),

    # PV PDF Generation
    path('pv/<int:pk>/pdf/', views.voucher_pdf, name='pdf'),

    # Payment Form (PF) CRUD
    path('pf/create/', views.FormCreateView.as_view(), name='pf_create'),
    path('pf/<int:pk>/', views.FormDetailView.as_view(), name='pf_detail'),
    path('pf/<int:pk>/edit/', views.FormEditView.as_view(), name='pf_edit'),
    path('pf/<int:pk>/delete/', views.form_delete, name='pf_delete'),
    path('pf/<int:pk>/repeat/', views.form_repeat, name='pf_repeat'),

    # PF Workflow actions
    path('pf/<int:pk>/submit/', views.form_submit, name='pf_submit'),
    path('pf/<int:pk>/approve/', views.form_approve, name='pf_approve'),

    # PF PDF Generation
    path('pf/<int:pk>/pdf/', views.form_pdf, name='pf_pdf'),

    # Reports
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/excel/', views.export_excel, name='export_excel'),
    path('reports/export/pdf/', views.export_pdf, name='export_pdf'),
]
