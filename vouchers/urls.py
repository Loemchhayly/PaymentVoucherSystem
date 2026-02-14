from django.urls import path
from . import views
from . import batch_views

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
    path('pf/<int:pk>/upload/', views.upload_form_attachment, name='upload_form_attachment'),
    path('pf/<int:pk>/attachments/<int:attachment_id>/', views.download_form_attachment,
         name='download_form_attachment'),
    path('pf/<int:pk>/attachments/<int:attachment_id>/delete/', views.delete_form_attachment,
         name='delete_form_attachment'),

    # Reports
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/excel/', views.export_excel, name='export_excel'),
    path('reports/export/pdf/', views.export_pdf, name='export_pdf'),

    # Bulk Approval
    path('bulk-approval/', views.bulk_approval_view, name='bulk_approval'),
    path('bulk-approval/action/', views.bulk_approval_action, name='bulk_approval_action'),

    # Batch Signature System
    path('batch/select/', batch_views.batch_select_documents, name='batch_select'),
    path('batch/create/', batch_views.batch_create, name='batch_create'),
    path('batch/list/', batch_views.fm_batch_list, name='fm_batch_list'),
    path('batch/all/', batch_views.all_batches_list, name='all_batches_list'),
    path('batch/<int:batch_id>/detail/', batch_views.batch_detail, name='batch_detail'),
    path('batch/<int:batch_id>/edit/', batch_views.batch_edit, name='batch_edit'),
    path('batch/<int:batch_id>/delete/', batch_views.batch_delete, name='batch_delete'),
    path('batch/<int:batch_id>/sign/', batch_views.batch_sign, name='batch_sign'),
    path('batch/<int:batch_id>/reject/', batch_views.batch_reject, name='batch_reject'),
    path('batch/<int:batch_id>/remove-document/', batch_views.batch_remove_document, name='batch_remove_document'),
    path('batch/<int:batch_id>/export-excel/', batch_views.batch_export_excel, name='batch_export_excel'),
    path('md-dashboard/', batch_views.md_dashboard, name='md_dashboard'),
]
