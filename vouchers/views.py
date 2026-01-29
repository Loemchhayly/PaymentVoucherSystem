from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from .models import PaymentVoucher, VoucherAttachment
from .forms import PaymentVoucherForm, VoucherLineItemFormSet, VoucherAttachmentForm, ApprovalActionForm
from workflow.state_machine import VoucherStateMachine


class VoucherCreateView(LoginRequiredMixin, CreateView):
    """View for creating new payment vouchers"""
    model = PaymentVoucher
    form_class = PaymentVoucherForm
    template_name = 'vouchers/voucher_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Payment Voucher'

        if self.request.POST:
            context['formset'] = VoucherLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = VoucherLineItemFormSet(instance=self.object)

        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        # Validate formset
        if not formset.is_valid():
            return self.form_invalid(form)

        # Set creator
        form.instance.created_by = self.request.user

        # Generate PV number immediately upon creation
        from workflow.state_machine import VoucherStateMachine
        form.instance.pv_number = VoucherStateMachine.generate_pv_number()

        self.object = form.save()

        # Save line items with auto-numbered lines
        formset.instance = self.object
        line_items = formset.save(commit=False)

        # Auto-number line items
        for i, item in enumerate(line_items, start=1):
            item.line_number = i
            item.save()

        # Handle deletions
        for obj in formset.deleted_objects:
            obj.delete()

        # Renumber remaining items
        self._renumber_line_items(self.object)

        # Handle file uploads
        files = self.request.FILES.getlist('attachments')
        if files:
            for file in files:
                VoucherAttachment.objects.create(
                    voucher=self.object,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    uploaded_by=self.request.user
                )
            messages.success(self.request, f'Voucher created successfully with {len(files)} attachment(s)!')
        else:
            messages.success(self.request, f'Voucher created successfully! You can add attachments from the detail page.')

        return redirect('vouchers:detail', pk=self.object.pk)

    def _renumber_line_items(self, voucher):
        """Renumber line items sequentially"""
        for i, item in enumerate(voucher.line_items.all().order_by('line_number'), start=1):
            if item.line_number != i:
                item.line_number = i
                item.save()


class VoucherEditView(LoginRequiredMixin, UpdateView):
    """View for editing existing vouchers"""
    model = PaymentVoucher
    form_class = PaymentVoucherForm
    template_name = 'vouchers/voucher_form.html'

    def get_queryset(self):
        # Only creator can edit their own vouchers
        return super().get_queryset().filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Voucher {self.object.pv_number or "DRAFT"}'

        # Check if editable
        if not self.object.is_editable():
            messages.error(self.request, 'This voucher cannot be edited.')
            return redirect('vouchers:detail', pk=self.object.pk)

        if self.request.POST:
            context['formset'] = VoucherLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = VoucherLineItemFormSet(instance=self.object)

        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()

        # FIXED: Delete all existing line items first to avoid unique constraint issues
        self.object.line_items.all().delete()

        # Now save the new line items from the formset
        formset.instance = self.object
        line_items = formset.save(commit=False)

        # Number them sequentially
        for i, item in enumerate(line_items, start=1):
            item.line_number = i
            item.save()

        # Handle file uploads
        files = self.request.FILES.getlist('attachments')
        if files:
            for file in files:
                VoucherAttachment.objects.create(
                    voucher=self.object,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    uploaded_by=self.request.user
                )
            messages.success(self.request, f'Voucher updated successfully with {len(files)} new attachment(s)!')
        else:
            messages.success(self.request, 'Voucher updated successfully!')

        return redirect('vouchers:detail', pk=self.object.pk)

class VoucherDetailView(LoginRequiredMixin, DetailView):
    """View for displaying voucher details"""
    model = PaymentVoucher
    template_name = 'vouchers/voucher_detail.html'
    context_object_name = 'voucher'

    def get_queryset(self):
        """Filter to only vouchers user has access to"""
        user = self.request.user

        if user.is_staff:
            return PaymentVoucher.objects.all()

        # User can see if: creator, current approver, or in approval history
        return PaymentVoucher.objects.filter(
            Q(created_by=user) |
            Q(current_approver=user) |
            Q(approval_history__actor=user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        voucher = self.object
        user = self.request.user

        # Calculate grand total
        context['grand_total'] = voucher.calculate_grand_total()

        # Permission checks
        context['can_submit'] = (
            voucher.status in ['DRAFT', 'ON_REVISION'] and
            user == voucher.created_by
        )

        context['can_approve'] = (
            voucher.current_approver == user and
            voucher.status.startswith('PENDING')
        )

        context['can_edit'] = (
            voucher.is_editable() and
            user == voucher.created_by
        )

        # Approval form for approvers
        if context['can_approve']:
            context['approval_form'] = ApprovalActionForm(user=user, voucher=voucher)

        # Approval history
        context['approval_history'] = voucher.approval_history.all().order_by('timestamp')

        return context


@login_required
def voucher_submit(request, pk):
    """Submit voucher for approval"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)

    # Check permission
    if voucher.created_by != request.user:
        messages.error(request, 'Only the creator can submit this voucher')
        return redirect('vouchers:detail', pk=pk)

    if voucher.status not in ['DRAFT', 'ON_REVISION']:
        messages.error(request, 'This voucher cannot be submitted in its current status')
        return redirect('vouchers:detail', pk=pk)

    # Check if has line items
    if not voucher.line_items.exists():
        messages.error(request, 'Please add at least one line item before submitting')
        return redirect('vouchers:edit', pk=pk)

    try:
        VoucherStateMachine.transition(voucher, 'submit', request.user)
        messages.success(request, f'Voucher {voucher.pv_number} submitted successfully for approval!')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('vouchers:detail', pk=pk)


@login_required
def voucher_approve(request, pk):
    """Handle approval actions (approve, reject, return)"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)

    # Check permission
    if voucher.current_approver != request.user:
        messages.error(request, 'You are not authorized to approve this voucher')
        return redirect('vouchers:detail', pk=pk)

    if request.method == 'POST':
        form = ApprovalActionForm(request.POST, user=request.user, voucher=voucher)

        if form.is_valid():
            action = form.cleaned_data['action']
            comments = form.cleaned_data.get('comments', '')

            # For GM, set requires_md_approval
            if request.user.role_level == 4 and action == 'approve':
                voucher.requires_md_approval = form.cleaned_data.get('requires_md_approval', False)
                voucher.save()

            try:
                VoucherStateMachine.transition(voucher, action, request.user, comments)
                messages.success(request, f'Voucher {action}d successfully!')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Invalid form submission. Please check your input.')

    return redirect('vouchers:detail', pk=pk)


@login_required
def upload_attachment(request, pk):
    """Upload multiple attachments to voucher"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk, created_by=request.user)

    if not voucher.is_editable():
        messages.error(request, 'Cannot add attachments to locked vouchers')
        return redirect('vouchers:detail', pk=pk)

    if request.method == 'POST':
        form = VoucherAttachmentForm(request.POST, request.FILES)

        if form.is_valid():
            files = form.cleaned_data['files']

            # Ensure files is a list
            if not isinstance(files, list):
                files = [files]

            success_count = 0

            for file in files:
                try:
                    attachment = VoucherAttachment(
                        voucher=voucher,
                        file=file,
                        filename=file.name,
                        file_size=file.size,
                        uploaded_by=request.user
                    )
                    attachment.save()
                    success_count += 1
                except Exception as e:
                    messages.warning(request, f'Failed to upload {file.name}: {str(e)}')

            if success_count > 0:
                if success_count == 1:
                    messages.success(request, 'File uploaded successfully!')
                else:
                    messages.success(request, f'{success_count} files uploaded successfully!')
        else:
            for error in form.errors.get('files', []):
                messages.error(request, error)

    return redirect('vouchers:detail', pk=pk)


@login_required
def delete_attachment(request, pk, attachment_id):
    """Delete an attachment"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk, created_by=request.user)
    attachment = get_object_or_404(VoucherAttachment, pk=attachment_id, voucher=voucher)

    if not voucher.is_editable():
        messages.error(request, 'Cannot delete attachments from locked vouchers')
        return redirect('vouchers:detail', pk=pk)

    if request.method == 'POST':
        filename = attachment.filename
        attachment.file.delete()  # Delete the actual file
        attachment.delete()  # Delete the database record
        messages.success(request, f'Attachment "{filename}" deleted successfully!')

    return redirect('vouchers:detail', pk=pk)


@login_required
def download_attachment(request, pk, attachment_id):
    """Secure attachment download"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    attachment = get_object_or_404(VoucherAttachment, pk=attachment_id, voucher=voucher)

    # Check access permissions
    user = request.user
    has_access = (
        voucher.created_by == user or
        voucher.current_approver == user or
        voucher.approval_history.filter(actor=user).exists() or
        user.is_staff
    )

    if not has_access:
        raise Http404("You don't have permission to access this file")

    return FileResponse(
        attachment.file.open('rb'),
        as_attachment=True,
        filename=attachment.filename
    )


@login_required
def voucher_pdf(request, pk):
    """Generate and download PDF for approved voucher"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)

    # Check access permissions
    user = request.user
    has_access = (
        voucher.created_by == user or
        voucher.current_approver == user or
        voucher.approval_history.filter(actor=user).exists() or
        user.is_staff
    )

    if not has_access:
        raise Http404("You don't have permission to access this voucher")

    # Only generate PDF for approved vouchers
    if voucher.status != 'APPROVED':
        messages.error(request, 'PDF can only be generated for approved vouchers')
        return redirect('vouchers:detail', pk=pk)

    # Generate PDF using your existing PDF generator
    from .pdf_generator import VoucherPDFGenerator
    return VoucherPDFGenerator.generate_pdf(voucher)


@login_required
def voucher_delete(request, pk):
    """Delete a draft voucher"""
    voucher = get_object_or_404(PaymentVoucher, pk=pk)

    # Only the creator can delete
    if voucher.created_by != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to delete this voucher")
        return redirect('vouchers:detail', pk=pk)

    # Only DRAFT vouchers can be deleted
    if voucher.status != 'DRAFT':
        messages.error(request, 'Only draft vouchers can be deleted')
        return redirect('vouchers:detail', pk=pk)

    if request.method == 'POST':
        voucher_number = voucher.pv_number or 'DRAFT'
        voucher.delete()
        messages.success(request, f'Voucher {voucher_number} has been deleted successfully')
        return redirect('dashboard:my_vouchers')

    # If GET request, show confirmation page
    return render(request, 'vouchers/voucher_confirm_delete.html', {
        'voucher': voucher
    })