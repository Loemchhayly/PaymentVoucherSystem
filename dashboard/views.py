from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView
from django.db.models import Q
from django.http import JsonResponse
from vouchers.models import PaymentVoucher, PaymentForm, SignatureBatch
from workflow.state_machine import VoucherStateMachine, FormStateMachine
from itertools import chain
from operator import attrgetter
from collections import defaultdict
from datetime import date
import json


class DashboardView(LoginRequiredMixin, ListView):
    """Main dashboard - MD/Admins see ALL vouchers, regular users see their own"""
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        search_query = self.request.GET.get('search', '').strip()
        search_field = self.request.GET.get('search_field', 'all')

        # Base querysets
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.all()
            pf_queryset = PaymentForm.objects.all()
        else:
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

        # Apply search filter BEFORE pagination
        if search_query:
            pv_queryset = self._apply_search_filter(pv_queryset, search_query, search_field, 'pv')
            pf_queryset = self._apply_search_filter(pf_queryset, search_query, search_field, 'pf')

        # Filter by doc_type
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

    def _apply_search_filter(self, queryset, query, field, doc_type):
        """Apply search filters based on selected field"""
        from decimal import Decimal, InvalidOperation

        if field == 'number':
            # Search in document number
            if doc_type == 'pv':
                return queryset.filter(pv_number__icontains=query)
            else:
                return queryset.filter(pf_number__icontains=query)

        elif field == 'payee':
            # Search in payee name
            return queryset.filter(payee_name__icontains=query)

        elif field == 'amount':
            # Search in amount
            try:
                amount_decimal = Decimal(query.replace(',', ''))
                return queryset.filter(
                    Q(line_items__amount=amount_decimal) |
                    Q(line_items__amount__icontains=query)
                ).distinct()
            except (InvalidOperation, ValueError):
                return queryset.filter(line_items__amount__icontains=query).distinct()

        elif field == 'date':
            # Search in dates
            return queryset.filter(
                Q(created_at__icontains=query) |
                Q(payment_date__icontains=query)
            )

        else:  # field == 'all'
            # Search in all fields
            q_filter = Q()

            # Document number
            if doc_type == 'pv':
                q_filter |= Q(pv_number__icontains=query)
            else:
                q_filter |= Q(pf_number__icontains=query)

            # Payee name
            q_filter |= Q(payee_name__icontains=query)

            # Amount
            try:
                amount_decimal = Decimal(query.replace(',', ''))
                q_filter |= Q(line_items__amount=amount_decimal)
            except (InvalidOperation, ValueError):
                pass
            q_filter |= Q(line_items__amount__icontains=query)

            # Date
            q_filter |= Q(created_at__icontains=query)
            q_filter |= Q(payment_date__icontains=query)

            return queryset.filter(q_filter).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from itertools import chain
        from operator import attrgetter
        from datetime import date
        from decimal import Decimal
        from django.db.models import Sum, Case, When, F, DecimalField
        from django.db.models.functions import TruncMonth

        # ── Base querysets ──
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

        # ── Stat counts ──
        if user.role_level == 5:
            pending_vouchers = 0
            pending_forms = 0
            pending_batches = SignatureBatch.objects.filter(status='PENDING').count()
        else:
            pending_vouchers = pv_base.filter(current_approver=user).count()
            pending_forms = pf_base.filter(current_approver=user).count()
            pending_batches = 0

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
        context['draft_count'] = (
                pv_base.filter(created_by=user, status__in=['DRAFT', 'ON_REVISION']).count() +
                pf_base.filter(created_by=user, status__in=['DRAFT', 'ON_REVISION']).count()
        )

        # ── Pending docs panel ──
        if user.role_level == 5:
            context['pending_docs'] = []
        else:
            pending_pvs = PaymentVoucher.objects.filter(
                current_approver=user,
                status__startswith='PENDING'
            ).order_by('-created_at')

            pending_pfs = PaymentForm.objects.filter(
                current_approver=user,
                status__startswith='PENDING'
            ).order_by('-created_at')

            context['pending_docs'] = sorted(
                chain(pending_pvs, pending_pfs),
                key=attrgetter('created_at'),
                reverse=True
            )[:5]

        # ── Fiscal year setup (Apr → Mar) ──
        today = date.today()
        if today.month >= 4:
            fy_start = date(today.year, 4, 1)
        else:
            fy_start = date(today.year - 1, 4, 1)
        fy_end = date(fy_start.year + 1, 3, 31)

        # Fiscal month order: APR=4, MAY=5 ... MAR=3
        fiscal_months = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
        month_abbr = {1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN',
                      7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'}

        # VAT-aware total expression
        vat_expr = Sum(
            Case(
                When(vat_applicable=True, then=F('amount') * Decimal('1.1')),
                default=F('amount'),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )

        # ── Monthly Disbursement ──
        pv_monthly = (
            PaymentVoucher.objects.filter(
                status='APPROVED',
                payment_date__gte=fy_start,
                payment_date__lte=fy_end
            )
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum(
                Case(
                    When(
                        line_items__vat_applicable=True,
                        then=F('line_items__amount') * Decimal('1.1')
                    ),
                    default=F('line_items__amount'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),
                filter=__import__('django.db.models', fromlist=['Q']).Q(line_items__currency='USD')
            ))
            .values('month', 'total')
        )

        pf_monthly = (
            PaymentForm.objects.filter(
                status='APPROVED',
                payment_date__gte=fy_start,
                payment_date__lte=fy_end
            )
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum(
                Case(
                    When(
                        line_items__vat_applicable=True,
                        then=F('line_items__amount') * Decimal('1.1')
                    ),
                    default=F('line_items__amount'),
                    output_field=DecimalField(max_digits=14, decimal_places=2)
                ),
                filter=__import__('django.db.models', fromlist=['Q']).Q(line_items__currency='USD')
            ))
            .values('month', 'total')
        )

        # Combine into dict keyed by month number
        monthly_totals = {m: Decimal('0') for m in fiscal_months}
        for row in pv_monthly:
            if row['month'] and row['total']:
                monthly_totals[row['month'].month] = (
                        monthly_totals.get(row['month'].month, Decimal('0')) + row['total']
                )
        for row in pf_monthly:
            if row['month'] and row['total']:
                monthly_totals[row['month'].month] = (
                        monthly_totals.get(row['month'].month, Decimal('0')) + row['total']
                )

        context['chart_labels'] = [month_abbr[m] for m in fiscal_months]
        context['chart_data'] = [float(monthly_totals[m]) for m in fiscal_months]
        context['chart_current_month'] = month_abbr[today.month]

        # ── By Department Donut (current month, approved, USD) ──
        month_start = date(today.year, today.month, 1)
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1)
        else:
            month_end = date(today.year, today.month + 1, 1)

        from vouchers.models import VoucherLineItem, FormLineItem

        pv_dept = (
            VoucherLineItem.objects
            .filter(
                voucher__status='APPROVED',
                voucher__payment_date__gte=month_start,
                voucher__payment_date__lt=month_end,
                currency='USD'
            )
            .values('department__name')
            .annotate(total=vat_expr)
            .order_by('-total')
        )

        pf_dept = (
            FormLineItem.objects
            .filter(
                payment_form__status='APPROVED',
                payment_form__payment_date__gte=month_start,
                payment_form__payment_date__lt=month_end,
                currency='USD'
            )
            .values('department__name')
            .annotate(total=vat_expr)
            .order_by('-total')
        )

        # Merge department totals
        dept_totals = {}
        for row in list(pv_dept) + list(pf_dept):
            name = row['department__name'] or 'Unknown'
            dept_totals[name] = dept_totals.get(name, Decimal('0')) + (row['total'] or Decimal('0'))

        # Sort, top 5 + Other
        sorted_depts = sorted(dept_totals.items(), key=lambda x: x[1], reverse=True)
        top5 = sorted_depts[:5]
        others = sorted_depts[5:]
        if others:
            other_total = sum(v for _, v in others)
            top5.append(('Other', other_total))

        grand_total = sum(v for _, v in top5) or Decimal('1')
        colors = ['#06b6d4', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444', '#3b82f6']

        donut_data = [
            {
                'name': name,
                'total': float(total),
                'pct': round(float(total / grand_total * 100), 1),
                'color': colors[i % len(colors)],
            }
            for i, (name, total) in enumerate(top5)
            if total > 0
        ]

        context['donut_data'] = donut_data
        context['donut_grand_usd'] = float(grand_total)

        # Add search parameters to context
        context['search_query'] = self.request.GET.get('search', '')
        context['search_field'] = self.request.GET.get('search_field', 'all')

        return context


# ── All other list views unchanged ──

class PendingActionView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'role_level') and request.user.role_level == 5:
            from django.shortcuts import redirect
            return redirect('vouchers:md_dashboard')
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        pv_queryset = PaymentVoucher.objects.filter(current_approver=user, status__startswith='PENDING')
        pf_queryset = PaymentForm.objects.filter(current_approver=user, status__startswith='PENDING')

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Pending My Action'
        return context


class InProgressView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.filter(status__startswith='PENDING')
            pf_queryset = PaymentForm.objects.filter(status__startswith='PENDING')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status__startswith='PENDING').distinct()
            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status__startswith='PENDING').distinct()

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'In Progress'
        return context


class ApprovedView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.filter(status='APPROVED')
            pf_queryset = PaymentForm.objects.filter(status='APPROVED')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status='APPROVED').distinct()
            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status='APPROVED').distinct()

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('pv_number'), reverse=False)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('pf_number'), reverse=False)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Approved Vouchers & Forms'
        return context


class CancelledView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.filter(status='REJECTED')
            pf_queryset = PaymentForm.objects.filter(status='REJECTED')
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status='REJECTED').distinct()
            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).filter(status='REJECTED').distinct()

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Rejected Vouchers & Forms'
        return context


class MyVouchersView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        doc_type = self.request.GET.get('doc_type', 'all')
        pv_queryset = PaymentVoucher.objects.filter(created_by=self.request.user)
        pf_queryset = PaymentForm.objects.filter(created_by=self.request.user)

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Vouchers & Forms'
        return context


class MyDraftsView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        doc_type = self.request.GET.get('doc_type', 'all')
        pv_queryset = PaymentVoucher.objects.filter(created_by=self.request.user, status__in=['DRAFT', 'ON_REVISION'])
        pf_queryset = PaymentForm.objects.filter(created_by=self.request.user, status__in=['DRAFT', 'ON_REVISION'])

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('updated_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('updated_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('updated_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Drafts'
        return context


class AllVouchersView(LoginRequiredMixin, ListView):
    template_name = 'dashboard/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        doc_type = self.request.GET.get('doc_type', 'all')
        if user.is_staff or user.role_level == 5:
            pv_queryset = PaymentVoucher.objects.all()
            pf_queryset = PaymentForm.objects.all()
        else:
            pv_queryset = PaymentVoucher.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).distinct()
            pf_queryset = PaymentForm.objects.filter(
                Q(created_by=user)|Q(current_approver=user)|Q(approval_history__actor=user)
            ).distinct()

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

        if doc_type == 'pv':
            return sorted(pv_queryset, key=attrgetter('created_at'), reverse=True)
        elif doc_type == 'pf':
            return sorted(pf_queryset, key=attrgetter('created_at'), reverse=True)
        return sorted(chain(pv_queryset, pf_queryset), key=attrgetter('created_at'), reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'All Recent Documents'
        return context


@login_required
def bulk_submit_drafts(request):
    """Handle bulk submission of draft documents"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method")
        return redirect('dashboard:my_drafts')

    user = request.user
    comments = request.POST.get('comments', '').strip()

    # Get selected document IDs
    pv_ids = request.POST.getlist('pv_ids[]')
    pf_ids = request.POST.getlist('pf_ids[]')

    if not pv_ids and not pf_ids:
        messages.error(request, "No documents selected")
        return redirect('dashboard:my_drafts')

    success_count = 0
    error_count = 0
    errors = []

    # Process Payment Vouchers
    for pv_id in pv_ids:
        try:
            voucher = PaymentVoucher.objects.get(pk=pv_id)

            # Security check: Only the creator can submit their own drafts
            if voucher.created_by != user:
                errors.append(f"PV {voucher.pv_number or pv_id}: You can only submit your own drafts")
                error_count += 1
                continue

            # Check if document is in DRAFT or ON_REVISION status
            if voucher.status not in ['DRAFT', 'ON_REVISION']:
                errors.append(f"PV {voucher.pv_number or pv_id}: Not a draft (status: {voucher.get_status_display()})")
                error_count += 1
                continue

            # Check if can submit
            can_do, error = VoucherStateMachine.can_transition(voucher, 'submit', user)
            if not can_do:
                errors.append(f"PV {voucher.pv_number or pv_id}: {error}")
                error_count += 1
                continue

            # Submit the document
            VoucherStateMachine.transition(voucher, 'submit', user, comments)
            success_count += 1

        except PaymentVoucher.DoesNotExist:
            errors.append(f"PV ID {pv_id}: Not found")
            error_count += 1
        except Exception as e:
            errors.append(f"PV ID {pv_id}: {str(e)}")
            error_count += 1

    # Process Payment Forms
    for pf_id in pf_ids:
        try:
            payment_form = PaymentForm.objects.get(pk=pf_id)

            # Security check: Only the creator can submit their own drafts
            if payment_form.created_by != user:
                errors.append(f"PF {payment_form.pf_number or pf_id}: You can only submit your own drafts")
                error_count += 1
                continue

            # Check if document is in DRAFT or ON_REVISION status
            if payment_form.status not in ['DRAFT', 'ON_REVISION']:
                errors.append(f"PF {payment_form.pf_number or pf_id}: Not a draft (status: {payment_form.get_status_display()})")
                error_count += 1
                continue

            # Check if can submit
            can_do, error = FormStateMachine.can_transition(payment_form, 'submit', user)
            if not can_do:
                errors.append(f"PF {payment_form.pf_number or pf_id}: {error}")
                error_count += 1
                continue

            # Submit the document
            FormStateMachine.transition(payment_form, 'submit', user, comments)
            success_count += 1

        except PaymentForm.DoesNotExist:
            errors.append(f"PF ID {pf_id}: Not found")
            error_count += 1
        except Exception as e:
            errors.append(f"PF ID {pf_id}: {str(e)}")
            error_count += 1

    # Display results
    if success_count > 0:
        messages.success(request, f"Successfully submitted {success_count} document(s) for approval")

    if error_count > 0:
        error_msg = f"{error_count} document(s) could not be submitted"
        if errors:
            error_msg += ":<br>" + "<br>".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                error_msg += f"<br>...and {len(errors) - 5} more error(s)"
        messages.error(request, error_msg)

    return redirect('dashboard:my_drafts')


@login_required
def dashboard_search(request):
    """Search ALL documents the user has access to"""
    query = request.GET.get('q', '').strip()
    doc_type = request.GET.get('doc_type', 'all')

    if not query:
        return JsonResponse({'success': False, 'error': 'No search query provided'})

    user = request.user

    # Base querysets - same logic as DashboardView
    if user.is_staff or user.role_level == 5:
        pv_queryset = PaymentVoucher.objects.all()
        pf_queryset = PaymentForm.objects.all()
    else:
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

    # Search across number and payee
    # Search PV
    pv_queryset = pv_queryset.filter(
        Q(pv_number__icontains=query) |
        Q(payee_name__icontains=query)
    )

    # Search PF
    pf_queryset = pf_queryset.filter(
        Q(pf_number__icontains=query) |
        Q(payee_name__icontains=query)
    )

    # Filter by doc_type
    if doc_type == 'pv':
        combined = list(pv_queryset)
    elif doc_type == 'pf':
        combined = list(pf_queryset)
    else:
        combined = list(chain(pv_queryset, pf_queryset))

    # Sort by created_at descending
    combined = sorted(combined, key=attrgetter('created_at'), reverse=True)

    # Limit to 100 results to avoid performance issues
    combined = combined[:100]

    # Build JSON response
    results = []
    for doc in combined:
        is_pf = hasattr(doc, 'pf_number') and doc.pf_number

        # Get currency from first line item
        currency = 'USD'
        if doc.line_items.exists():
            currency = doc.line_items.first().currency

        results.append({
            'id': doc.pk,
            'type': 'pf' if is_pf else 'pv',
            'number': doc.pf_number if is_pf else doc.pv_number or 'DRAFT',
            'payee': doc.payee_name,
            'amount': doc.get_grand_total_display(),
            'status': doc.status,
            'status_display': doc.get_status_display(),
            'date': doc.created_at.strftime('%b %d, %Y'),
            'detail_url': f'/vouchers/pf/{doc.pk}/' if is_pf else f'/vouchers/{doc.pk}/',
            'repeat_url': f'/vouchers/pf/{doc.pk}/repeat/' if is_pf else f'/vouchers/{doc.pk}/repeat/',
        })

    return JsonResponse({
        'success': True,
        'count': len(results),
        'results': results
    })