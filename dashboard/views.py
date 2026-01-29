from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from vouchers.models import PaymentVoucher


class DashboardView(LoginRequiredMixin, ListView):
    """Main dashboard view"""
    model = PaymentVoucher
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return PaymentVoucher.objects.all()

        # User can see vouchers they created, are assigned to, or have approved
        return PaymentVoucher.objects.filter(
            Q(created_by=user) |
            Q(current_approver=user) |
            Q(approval_history__actor=user)
        ).distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Base queryset for user's accessible vouchers
        if user.is_staff:
            base_queryset = PaymentVoucher.objects.all()
        else:
            base_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).distinct()

        # Summary counts (only vouchers user has access to)
        context['pending_my_action'] = base_queryset.filter(
            current_approver=user
        ).count()

        context['my_vouchers'] = base_queryset.filter(
            created_by=user
        ).count()

        context['in_progress'] = base_queryset.filter(
            status__startswith='PENDING'
        ).count()

        context['approved_count'] = base_queryset.filter(
            status='APPROVED'
        ).count()

        return context


class PendingActionView(LoginRequiredMixin, ListView):
    """Vouchers pending user's action"""
    model = PaymentVoucher
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        queryset = PaymentVoucher.objects.filter(
            current_approver=self.request.user
        )

        # Apply search filters
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            queryset = queryset.filter(pv_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            queryset = queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pending My Action'
        return context


class InProgressView(LoginRequiredMixin, ListView):
    """All in-progress vouchers (that user has access to)"""
    model = PaymentVoucher
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Base queryset - only vouchers user has access to
        if user.is_staff:
            queryset = PaymentVoucher.objects.filter(status__startswith='PENDING')
        else:
            queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status__startswith='PENDING').distinct()

        # Apply search filters
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            queryset = queryset.filter(pv_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            queryset = queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'In Progress'
        return context


class ApprovedView(LoginRequiredMixin, ListView):
    """Approved vouchers (that user has access to)"""
    model = PaymentVoucher
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Base queryset - only vouchers user has access to
        if user.is_staff:
            queryset = PaymentVoucher.objects.filter(status='APPROVED')
        else:
            queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='APPROVED').distinct()

        # Apply search filters
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            queryset = queryset.filter(pv_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            queryset = queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Approved Vouchers'
        return context


class CancelledView(LoginRequiredMixin, ListView):
    """Rejected vouchers (that user has access to)"""
    model = PaymentVoucher
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Base queryset - only vouchers user has access to
        if user.is_staff:
            queryset = PaymentVoucher.objects.filter(status='REJECTED')
        else:
            queryset = PaymentVoucher.objects.filter(
                Q(created_by=user) |
                Q(current_approver=user) |
                Q(approval_history__actor=user)
            ).filter(status='REJECTED').distinct()

        # Apply search filters
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            queryset = queryset.filter(pv_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            queryset = queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Rejected Vouchers'
        return context


class MyVouchersView(LoginRequiredMixin, ListView):
    """User's own vouchers"""
    model = PaymentVoucher
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        queryset = PaymentVoucher.objects.filter(
            created_by=self.request.user
        )

        # Apply search filters
        pv_number = self.request.GET.get('pv_number', '').strip()
        if pv_number:
            queryset = queryset.filter(pv_number__icontains=pv_number)

        payee_name = self.request.GET.get('payee_name', '').strip()
        if payee_name:
            queryset = queryset.filter(payee_name__icontains=payee_name)

        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Vouchers'
        return context
