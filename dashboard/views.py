from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from vouchers.models import PaymentVoucher, PaymentForm, SignatureBatch
from itertools import chain
from operator import attrgetter


class DashboardView(LoginRequiredMixin, ListView):
    """Main dashboard - MD/Admins see ALL vouchers, regular users see their own"""
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')

        # MD and Admins see ALL vouchers (including history)
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.all()
            pf_queryset = PaymentForm.objects.all()
        else:
            # Regular users see only their vouchers (created or involved with)
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).distinct()
            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).distinct()

        # Filter by document type
        if doc_type == 'pv':
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Base queryset for stats (same as displayed vouchers)
        if user.is_staff or user.role_level == 5:
            pv_base = PaymentVoucher.objects.all()
            pf_base = PaymentForm.objects.all()
        else:
            pv_base = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).distinct()
            pf_base = PaymentForm.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).distinct()

        # Summary counts
        pending_vouchers = pv_base.filter(current_approver=user).count()
        pending_forms = pf_base.filter(current_approver=user).count()

        # Add pending signature batches for MD
        pending_batches = 0
        if user.role_level == 5:  # MD
            pending_batches = SignatureBatch.objects.filter(status='PENDING').count()

        context['pending_my_action'] = pending_vouchers + pending_forms + pending_batches
        context['pending_batches'] = pending_batches

        context['my_created_count'] = (
            pv_base.filter(created_by=user).count() +
            pf_base.filter(created_by=user).count()
        )

        context['in_progress'] = (
            pv_base.filter(status__startswith='PENDING').count() +
            pf_base.filter(status__startswith='PENDING').count()
        )

        context['approved_count'] = (
            pv_base.filter(status='APPROVED').count() +
            pf_base.filter(status='APPROVED').count()
        )

        return context


class PendingActionView(LoginRequiredMixin, ListView):
    """Vouchers and forms pending user's action"""
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        # Check document type filter
        doc_type = self.request.GET.get('doc_type', 'all')

        # Get Payment Vouchers pending user's action
        pv_queryset = PaymentVoucher.objects.filter(
            current_approver=self.request.user
        )

        # Get Payment Forms pending user's action
        pf_queryset = PaymentForm.objects.filter(
            current_approver=self.request.user
        )

        # Apply search filters to both
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            pv_queryset = pv_queryset.filter(pv_number__icontains=pv_number)
            pf_queryset = pf_queryset.filter(pf_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            pv_queryset = pv_queryset.filter(payee_name__icontains=payee_name)
            pf_queryset = pf_queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            pv_queryset = pv_queryset.filter(payment_date__gte=date_from)
            pf_queryset = pf_queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            pv_queryset = pv_queryset.filter(payment_date__lte=date_to)
            pf_queryset = pf_queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            pv_queryset = pv_queryset.filter(status=status)
            pf_queryset = pf_queryset.filter(status=status)

        # Filter by document type
        if doc_type == 'pv':
            # Only Payment Vouchers
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            # Only Payment Forms
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            # All documents (default)
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pending My Action'
        return context


class InProgressView(LoginRequiredMixin, ListView):
    """All in-progress vouchers and forms (that user has access to)"""
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Check document type filter
        doc_type = self.request.GET.get('doc_type', 'all')

        # Base queryset - only vouchers/forms user has access to
        if user.is_staff:
            pv_queryset = PaymentVoucher.objects.filter(status__startswith='PENDING')
            pf_queryset = PaymentForm.objects.filter(status__startswith='PENDING')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status__startswith='PENDING').distinct()

            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status__startswith='PENDING').distinct()

        # Apply search filters to both
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            pv_queryset = pv_queryset.filter(pv_number__icontains=pv_number)
            pf_queryset = pf_queryset.filter(pf_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            pv_queryset = pv_queryset.filter(payee_name__icontains=payee_name)
            pf_queryset = pf_queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            pv_queryset = pv_queryset.filter(payment_date__gte=date_from)
            pf_queryset = pf_queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            pv_queryset = pv_queryset.filter(payment_date__lte=date_to)
            pf_queryset = pf_queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            pv_queryset = pv_queryset.filter(status=status)
            pf_queryset = pf_queryset.filter(status=status)

        # Filter by document type
        if doc_type == 'pv':
            # Only Payment Vouchers
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            # Only Payment Forms
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            # All documents (default)
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'In Progress'
        return context


class ApprovedView(LoginRequiredMixin, ListView):
    """Approved vouchers and forms (that user has access to)"""
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Check document type filter
        doc_type = self.request.GET.get('doc_type', 'all')

        # Base queryset - only vouchers/forms user has access to
        if user.is_staff:
            pv_queryset = PaymentVoucher.objects.filter(status='APPROVED')
            pf_queryset = PaymentForm.objects.filter(status='APPROVED')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='APPROVED').distinct()

            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='APPROVED').distinct()

        # Apply search filters to both
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            pv_queryset = pv_queryset.filter(pv_number__icontains=pv_number)
            pf_queryset = pf_queryset.filter(pf_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            pv_queryset = pv_queryset.filter(payee_name__icontains=payee_name)
            pf_queryset = pf_queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            pv_queryset = pv_queryset.filter(payment_date__gte=date_from)
            pf_queryset = pf_queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            pv_queryset = pv_queryset.filter(payment_date__lte=date_to)
            pf_queryset = pf_queryset.filter(payment_date__lte=date_to)

        # Filter by document type
        if doc_type == 'pv':
            # Only Payment Vouchers
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            # Only Payment Forms
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            # All documents (default)
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Approved Vouchers & Forms'
        return context


class CancelledView(LoginRequiredMixin, ListView):
    """Rejected vouchers and forms (that user has access to)"""
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Check document type filter
        doc_type = self.request.GET.get('doc_type', 'all')

        # Base queryset - only vouchers/forms user has access to
        if user.is_staff:
            pv_queryset = PaymentVoucher.objects.filter(status='REJECTED')
            pf_queryset = PaymentForm.objects.filter(status='REJECTED')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='REJECTED').distinct()

            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='REJECTED').distinct()

        # Apply search filters to both
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            pv_queryset = pv_queryset.filter(pv_number__icontains=pv_number)
            pf_queryset = pf_queryset.filter(pf_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            pv_queryset = pv_queryset.filter(payee_name__icontains=payee_name)
            pf_queryset = pf_queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            pv_queryset = pv_queryset.filter(payment_date__gte=date_from)
            pf_queryset = pf_queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            pv_queryset = pv_queryset.filter(payment_date__lte=date_to)
            pf_queryset = pf_queryset.filter(payment_date__lte=date_to)

        # Filter by document type
        if doc_type == 'pv':
            # Only Payment Vouchers
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            # Only Payment Forms
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            # All documents (default)
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Rejected Vouchers & Forms'
        return context


class MyVouchersView(LoginRequiredMixin, ListView):
    """User's own vouchers and payment forms"""
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        # Check document type filter
        doc_type = self.request.GET.get('doc_type', 'all')

        # Get Payment Vouchers
        pv_queryset = PaymentVoucher.objects.filter(
            created_by=self.request.user
        )

        # Get Payment Forms
        pf_queryset = PaymentForm.objects.filter(
            created_by=self.request.user
        )

        # Apply search filters to both
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            pv_queryset = pv_queryset.filter(pv_number__icontains=pv_number)
            pf_queryset = pf_queryset.filter(pf_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            pv_queryset = pv_queryset.filter(payee_name__icontains=payee_name)
            pf_queryset = pf_queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            pv_queryset = pv_queryset.filter(payment_date__gte=date_from)
            pf_queryset = pf_queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            pv_queryset = pv_queryset.filter(payment_date__lte=date_to)
            pf_queryset = pf_queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            pv_queryset = pv_queryset.filter(status=status)
            pf_queryset = pf_queryset.filter(status=status)

        # Filter by document type
        if doc_type == 'pv':
            # Only Payment Vouchers
            combined = sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            # Only Payment Forms
            combined = sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        else:
            # All documents (default)
            combined = sorted(
                chain(pv_queryset, pf_queryset),
                key=attrgetter('created_at'),
                reverse=True
            )

        return combined

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Vouchers & Forms'
        return context
