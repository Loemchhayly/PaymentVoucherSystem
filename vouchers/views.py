from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from .models import PaymentVoucher, VoucherAttachment, PaymentForm, FormAttachment
from .forms import (PaymentVoucherForm, VoucherLineItemFormSet, VoucherAttachmentForm, ApprovalActionForm,
                   PaymentFormForm, FormLineItemFormSet, FormAttachmentForm)
from workflow.state_machine import VoucherStateMachine, FormStateMachine


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

        # Generate PV number immediately upon creation (using payment_date)
        from workflow.state_machine import VoucherStateMachine
        form.instance.pv_number = VoucherStateMachine.generate_pv_number(form.instance)

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


@login_required
def voucher_repeat(request, pk):
    """Create a new voucher pre-filled with data from an existing voucher"""
    # Get the source voucher
    source_voucher = get_object_or_404(PaymentVoucher, pk=pk)

    # Check if user has access to this voucher
    if not (request.user.is_staff or
            source_voucher.created_by == request.user or
            source_voucher.current_approver == request.user or
            source_voucher.approval_history.filter(actor=request.user).exists()):
        messages.error(request, 'You do not have permission to repeat this voucher.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = PaymentVoucherForm(request.POST, user=request.user)
        formset = VoucherLineItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Create new voucher
                new_voucher = form.save(commit=False)
                new_voucher.created_by = request.user
                new_voucher.pv_number = VoucherStateMachine.generate_pv_number(new_voucher)
                new_voucher.save()

                # Save line items
                formset.instance = new_voucher
                line_items = formset.save(commit=False)
                for i, item in enumerate(line_items, start=1):
                    item.line_number = i
                    item.save()

                # Handle attachments
                files = request.FILES.getlist('attachments')
                if files:
                    for file in files:
                        VoucherAttachment.objects.create(
                            voucher=new_voucher,
                            file=file,
                            filename=file.name,
                            file_size=file.size,
                            uploaded_by=request.user
                        )

                messages.success(request, f'New voucher created from PV {source_voucher.pv_number}!')
                return redirect('vouchers:detail', pk=new_voucher.pk)
    else:
        # Pre-fill form with source voucher data
        initial_data = {
            'payee_name': source_voucher.payee_name,
            'payment_date': source_voucher.payment_date,
            'bank_address': source_voucher.bank_address,
            'bank_name': source_voucher.bank_name,
            'bank_account_number': source_voucher.bank_account_number,
        }
        form = PaymentVoucherForm(initial=initial_data, user=request.user)

        # Pre-fill formset with source line items
        formset = VoucherLineItemFormSet(
            queryset=source_voucher.line_items.none(),
            initial=[{
                'description': item.description,
                'department': item.department_id,
                'program': item.program,
                'amount': item.amount,
                'currency': item.currency,
                'vat_applicable': item.vat_applicable,
            } for item in source_voucher.line_items.all()]
        )

    context = {
        'form': form,
        'formset': formset,
        'title': f'Repeat Voucher from PV {source_voucher.pv_number}',
        'source_voucher': source_voucher,
    }
    return render(request, 'vouchers/voucher_form.html', context)


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

        # Handle deleted attachments FIRST (before saving anything else)
        deleted_attachments_ids = self.request.POST.get('deleted_attachments', '')
        if deleted_attachments_ids:
            ids_list = [int(id.strip()) for id in deleted_attachments_ids.split(',') if id.strip()]
            if ids_list:
                # Delete the attachments
                attachments_to_delete = VoucherAttachment.objects.filter(
                    id__in=ids_list,
                    voucher=self.object
                )

                deleted_count = 0
                for attachment in attachments_to_delete:
                    try:
                        # Delete the actual file from storage
                        if attachment.file:
                            attachment.file.delete(save=False)
                        # Delete the database record
                        attachment.delete()
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting attachment: {e}")

                if deleted_count > 0:
                    messages.info(self.request, f'{deleted_count} existing attachment(s) removed.')

        # Save the voucher header
        self.object = form.save()

        # ✅ FIX UNIQUE CONSTRAINT: Move ALL existing line items to temporary numbers FIRST
        # This prevents conflicts when we renumber
        existing_items = self.object.line_items.all()
        for i, item in enumerate(existing_items, start=10000):
            item.line_number = i
            item.save(update_fields=['line_number'])

        # Set the formset instance
        formset.instance = self.object

        # Save the formset to get access to deleted_objects
        saved_items = formset.save(commit=False)

        # Delete items marked for deletion in the formset
        for obj in formset.deleted_objects:
            obj.delete()

        # Save new/updated line items (they now have safe temporary numbers)
        for item in saved_items:
            item.save()

        # Now renumber ALL remaining items sequentially from 1
        all_remaining_items = self.object.line_items.all().order_by('id')
        for i, item in enumerate(all_remaining_items, start=1):
            item.line_number = i
            item.save(update_fields=['line_number'])

        # Save many-to-many relationships if any
        formset.save_m2m()

        # Handle NEW file uploads
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

    def _renumber_line_items(self, voucher):
        """Renumber line items sequentially"""
        for i, item in enumerate(voucher.line_items.all().order_by('id'), start=1):
            if item.line_number != i:
                item.line_number = i
                item.save(update_fields=['line_number'])
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

                # Redirect back to the page they came from (e.g., Pending My Action)
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)

            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Invalid form submission. Please check your input.')

    return redirect('vouchers:detail', pk=pk)


# ============================================================================
# PAYMENT FORM (PF) WORKFLOW ACTIONS
# ============================================================================

@login_required
def form_submit(request, pk):
    """Submit payment form for approval"""
    payment_form = get_object_or_404(PaymentForm, pk=pk)

    # Check permission
    if payment_form.created_by != request.user:
        messages.error(request, 'Only the creator can submit this form')
        return redirect('vouchers:pf_detail', pk=pk)

    if payment_form.status not in ['DRAFT', 'ON_REVISION']:
        messages.error(request, 'This form cannot be submitted in its current status')
        return redirect('vouchers:pf_detail', pk=pk)

    # Check if has line items
    if not payment_form.line_items.exists():
        messages.error(request, 'Please add at least one line item before submitting')
        return redirect('vouchers:pf_edit', pk=pk)

    try:
        FormStateMachine.transition(payment_form, 'submit', request.user)
        messages.success(request, f'Payment Form {payment_form.pf_number} submitted successfully for approval!')
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('vouchers:pf_detail', pk=pk)


@login_required
def form_approve(request, pk):
    """Handle approval actions for payment forms (approve, reject, return)"""
    payment_form = get_object_or_404(PaymentForm, pk=pk)

    # Check permission
    if payment_form.current_approver != request.user:
        messages.error(request, 'You are not authorized to approve this form')
        return redirect('vouchers:pf_detail', pk=pk)

    if request.method == 'POST':
        form = ApprovalActionForm(request.POST, user=request.user, voucher=payment_form)

        if form.is_valid():
            action = form.cleaned_data['action']
            comments = form.cleaned_data.get('comments', '')

            # For GM, set requires_md_approval
            if request.user.role_level == 4 and action == 'approve':
                payment_form.requires_md_approval = form.cleaned_data.get('requires_md_approval', False)
                payment_form.save()

            try:
                FormStateMachine.transition(payment_form, action, request.user, comments)
                messages.success(request, f'Payment Form {action}d successfully!')

                # Redirect back to the page they came from (e.g., Pending My Action)
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url:
                    return redirect(next_url)

            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Invalid form submission. Please check your input.')

    return redirect('vouchers:pf_detail', pk=pk)


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
def upload_form_attachment(request, pk):
    """Upload multiple attachments to payment form"""
    payment_form = get_object_or_404(PaymentForm, pk=pk, created_by=request.user)

    if not payment_form.is_editable():
        messages.error(request, 'Cannot add attachments to locked forms')
        return redirect('vouchers:pf_detail', pk=pk)

    if request.method == 'POST':
        form = FormAttachmentForm(request.POST, request.FILES)

        if form.is_valid():
            files = form.cleaned_data['files']

            # Ensure files is a list
            if not isinstance(files, list):
                files = [files]

            success_count = 0

            for file in files:
                try:
                    attachment = FormAttachment(
                        payment_form=payment_form,
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

    return redirect('vouchers:pf_detail', pk=pk)


@login_required
def delete_form_attachment(request, pk, attachment_id):
    """Delete a form attachment with proper error handling"""
    try:
        payment_form = get_object_or_404(PaymentForm, pk=pk, created_by=request.user)
        attachment = get_object_or_404(FormAttachment, pk=attachment_id, payment_form=payment_form)
    except PaymentForm.DoesNotExist:
        messages.error(request, f'Payment Form #{pk} not found.')
        return redirect('dashboard:home')
    except FormAttachment.DoesNotExist:
        messages.error(request, f'Attachment not found.')
        return redirect('vouchers:pf_detail', pk=pk)

    if not payment_form.is_editable():
        messages.error(request, 'Cannot delete attachments from locked forms')
        return redirect('vouchers:pf_detail', pk=pk)

    if request.method == 'POST':
        filename = attachment.filename
        try:
            attachment.file.delete()  # Delete the actual file
            attachment.delete()  # Delete the database record
            messages.success(request, f'Attachment "{filename}" deleted successfully!')
        except Exception as e:
            messages.error(request, f'Error deleting attachment: {str(e)}')

    return redirect('vouchers:pf_detail', pk=pk)


@login_required
def download_form_attachment(request, pk, attachment_id):
    """Secure attachment download for Payment Forms with proper error handling"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Try to get the payment form - this will raise 404 if not found
        payment_form = get_object_or_404(PaymentForm, pk=pk)

        # Try to get the attachment
        attachment = get_object_or_404(FormAttachment, pk=attachment_id, payment_form=payment_form)

        # Check access permissions
        user = request.user
        has_access = (
                payment_form.created_by == user or
                payment_form.current_approver == user or
                payment_form.approval_history.filter(actor=user).exists() or
                user.is_staff
        )

        if not has_access:
            logger.warning(
                f"Unauthorized form attachment access attempt: User {user.username} "
                f"tried to access attachment {attachment_id} for form {pk}"
            )
            raise Http404("You don't have permission to access this file")

        # Log successful download
        logger.info(
            f"Form attachment downloaded: {attachment.filename} by {user.username} "
            f"from form {payment_form.pf_number or pk}"
        )

        return FileResponse(
            attachment.file.open('rb'),
            as_attachment=True,
            filename=attachment.filename
        )

    except PaymentForm.DoesNotExist:
        # Log the missing form attempt
        logger.warning(
            f"404 - Payment Form not found: User {request.user.username} tried to access "
            f"form ID {pk} (attachment {attachment_id}). IP: {get_client_ip(request)}"
        )
        messages.error(
            request,
            f'Payment Form #{pk} not found. It may have been deleted or you may have '
            f'an outdated link. Please check the form list for the correct document.'
        )
        return redirect('dashboard:home')

    except FormAttachment.DoesNotExist:
        logger.warning(
            f"404 - Form attachment not found: User {request.user.username} tried to access "
            f"attachment {attachment_id} for form {pk}. IP: {get_client_ip(request)}"
        )
        messages.error(
            request,
            f'Attachment not found for payment form #{pk}. The file may have been deleted.'
        )
        return redirect('dashboard:home')


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


# ============================================================================
# PAYMENT FORM VIEWS (PF)
# ============================================================================

class FormCreateView(LoginRequiredMixin, CreateView):
    """View for creating new payment forms"""
    model = PaymentForm
    form_class = PaymentFormForm
    template_name = 'vouchers/pf/form_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Payment Form'

        if self.request.POST:
            context['formset'] = FormLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = FormLineItemFormSet(instance=self.object)

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

        # Generate PF number immediately upon creation (using payment_date)
        form.instance.pf_number = VoucherStateMachine.generate_pf_number(form.instance)

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
                FormAttachment.objects.create(
                    payment_form=self.object,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    uploaded_by=self.request.user
                )
            messages.success(self.request, f'Payment Form created successfully with {len(files)} attachment(s)!')
        else:
            messages.success(self.request, f'Payment Form created successfully! You can add attachments from the detail page.')

        return redirect('vouchers:pf_detail', pk=self.object.pk)

    def _renumber_line_items(self, payment_form):
        """Renumber line items sequentially"""
        for i, item in enumerate(payment_form.line_items.all().order_by('line_number'), start=1):
            if item.line_number != i:
                item.line_number = i
                item.save()


@login_required
def form_repeat(request, pk):
    """Create a new payment form pre-filled with data from an existing form"""
    # Get the source form
    source_form = get_object_or_404(PaymentForm, pk=pk)

    # Check if user has access to this form
    if not (request.user.is_staff or
            source_form.created_by == request.user or
            source_form.current_approver == request.user or
            source_form.approval_history.filter(actor=request.user).exists()):
        messages.error(request, 'You do not have permission to repeat this form.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = PaymentFormForm(request.POST, user=request.user)
        formset = FormLineItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                # Create new form
                new_form = form.save(commit=False)
                new_form.created_by = request.user
                new_form.pf_number = VoucherStateMachine.generate_pf_number(new_form)
                new_form.save()

                # Save line items
                formset.instance = new_form
                line_items = formset.save(commit=False)
                for i, item in enumerate(line_items, start=1):
                    item.line_number = i
                    item.save()

                # Handle attachments
                files = request.FILES.getlist('attachments')
                if files:
                    for file in files:
                        FormAttachment.objects.create(
                            payment_form=new_form,
                            file=file,
                            filename=file.name,
                            file_size=file.size,
                            uploaded_by=request.user
                        )

                messages.success(request, f'New payment form created from PF {source_form.pf_number}!')
                return redirect('vouchers:pf_detail', pk=new_form.pk)
    else:
        # Pre-fill form with source data
        initial_data = {
            'payee_name': source_form.payee_name,
            'payment_date': source_form.payment_date,
            'bank_address': source_form.bank_address,
            'bank_name': source_form.bank_name,
            'bank_account_number': source_form.bank_account_number,
        }
        form = PaymentFormForm(initial=initial_data, user=request.user)

        # Pre-fill formset with source line items
        formset = FormLineItemFormSet(
            queryset=source_form.line_items.none(),
            initial=[{
                'description': item.description,
                'department': item.department_id,
                'program': item.program,
                'amount': item.amount,
                'currency': item.currency,
                'vat_applicable': item.vat_applicable,
            } for item in source_form.line_items.all()]
        )

    context = {
        'form': form,
        'formset': formset,
        'title': f'Repeat Form from PF {source_form.pf_number}',
        'source_form': source_form,
    }
    return render(request, 'vouchers/pf/form_form.html', context)


class FormEditView(LoginRequiredMixin, UpdateView):
    """View for editing existing payment forms"""
    model = PaymentForm
    form_class = PaymentFormForm
    template_name = 'vouchers/pf/form_form.html'

    def get_queryset(self):
        # Only creator can edit their own forms
        return super().get_queryset().filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Payment Form {self.object.pf_number or "DRAFT"}'

        # Check if editable
        if not self.object.is_editable():
            messages.error(self.request, 'This payment form cannot be edited.')
            return redirect('vouchers:pf_detail', pk=self.object.pk)

        if self.request.POST:
            context['formset'] = FormLineItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = FormLineItemFormSet(instance=self.object)

        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():
            return self.form_invalid(form)

        # Handle deleted attachments FIRST
        deleted_attachments_ids = self.request.POST.get('deleted_attachments', '')
        if deleted_attachments_ids:
            ids_list = [int(id.strip()) for id in deleted_attachments_ids.split(',') if id.strip()]
            if ids_list:
                # Delete the attachments - Use FormAttachment for PaymentForm
                attachments_to_delete = FormAttachment.objects.filter(
                    id__in=ids_list,
                    payment_form=self.object
                )

                deleted_count = 0
                for attachment in attachments_to_delete:
                    try:
                        # Delete the actual file from storage
                        if attachment.file:
                            attachment.file.delete(save=False)
                        # Delete the database record
                        attachment.delete()
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting attachment: {e}")

                if deleted_count > 0:
                    messages.info(self.request, f'{deleted_count} existing attachment(s) removed.')

        # Save the payment form header
        self.object = form.save()

        # ✅ FIX UNIQUE CONSTRAINT: Move ALL existing line items to temporary numbers FIRST
        # This prevents conflicts when we renumber
        existing_items = self.object.line_items.all()
        for i, item in enumerate(existing_items, start=10000):
            item.line_number = i
            item.save(update_fields=['line_number'])

        # Set the formset instance
        formset.instance = self.object

        # Save the formset to get access to deleted_objects
        saved_items = formset.save(commit=False)

        # Delete items marked for deletion in the formset
        for obj in formset.deleted_objects:
            obj.delete()

        # Save new/updated line items (they now have safe temporary numbers)
        for item in saved_items:
            item.save()

        # Now renumber ALL remaining items sequentially from 1
        all_remaining_items = self.object.line_items.all().order_by('id')
        for i, item in enumerate(all_remaining_items, start=1):
            item.line_number = i
            item.save(update_fields=['line_number'])

        # Save many-to-many relationships if any
        formset.save_m2m()

        # Handle NEW file uploads
        files = self.request.FILES.getlist('attachments')
        if files:
            for file in files:
                FormAttachment.objects.create(
                    payment_form=self.object,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    uploaded_by=self.request.user
                )
            messages.success(self.request, f'Payment Form updated successfully with {len(files)} new attachment(s)!')
        else:
            messages.success(self.request, 'Payment Form updated successfully!')

        return redirect('vouchers:pf_detail', pk=self.object.pk)
    def _renumber_line_items(self, payment_form):
        """Renumber line items sequentially"""
        for i, item in enumerate(payment_form.line_items.all().order_by('id'), start=1):
            if item.line_number != i:
                item.line_number = i
                item.save(update_fields=['line_number'])


class FormDetailView(LoginRequiredMixin, DetailView):
    """View for displaying payment form details"""
    model = PaymentForm
    template_name = 'vouchers/pf/form_detail.html'
    context_object_name = 'payment_form'

    def get_queryset(self):
        """Filter to only forms user has access to"""
        user = self.request.user

        if user.is_staff:
            return PaymentForm.objects.all()

        # User can see if: creator, current approver, or in approval history
        return PaymentForm.objects.filter(
            Q(created_by=user) |
            Q(current_approver=user) |
            Q(approval_history__actor=user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_form = self.object
        user = self.request.user

        # Calculate grand total
        context['grand_total'] = payment_form.calculate_grand_total()

        # Permission checks
        context['can_submit'] = (
            payment_form.status in ['DRAFT', 'ON_REVISION'] and
            user == payment_form.created_by
        )

        context['can_approve'] = (
            payment_form.current_approver == user and
            payment_form.status.startswith('PENDING')
        )

        context['can_edit'] = (
            payment_form.is_editable() and
            user == payment_form.created_by
        )

        # Approval form for approvers
        if context['can_approve']:
            context['approval_form'] = ApprovalActionForm(user=user, voucher=payment_form)

        # Approval history
        context['approval_history'] = payment_form.approval_history.all().order_by('timestamp')

        return context


@login_required
def form_delete(request, pk):
    """Delete a draft payment form"""
    payment_form = get_object_or_404(PaymentForm, pk=pk)

    # Only the creator can delete
    if payment_form.created_by != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to delete this payment form")
        return redirect('vouchers:pf_detail', pk=pk)

    # Only DRAFT forms can be deleted
    if payment_form.status != 'DRAFT':
        messages.error(request, 'Only draft payment forms can be deleted')
        return redirect('vouchers:pf_detail', pk=pk)

    if request.method == 'POST':
        form_number = payment_form.pf_number or 'DRAFT'
        payment_form.delete()
        messages.success(request, f'Payment Form {form_number} has been deleted successfully')
        return redirect('dashboard:my_vouchers')

    # If GET request, show confirmation page
    return render(request, 'vouchers/pf/form_confirm_delete.html', {
        'payment_form': payment_form
    })


@login_required
def form_pdf(request, pk):
    """Generate and download PDF for approved payment form"""
    payment_form = get_object_or_404(PaymentForm, pk=pk)

    # Check access permissions
    user = request.user
    has_access = (
        payment_form.created_by == user or
        payment_form.current_approver == user or
        payment_form.approval_history.filter(actor=user).exists() or
        user.is_staff
    )

    if not has_access:
        raise Http404("You don't have permission to access this payment form")

    # Only generate PDF for approved forms
    if payment_form.status != 'APPROVED':
        messages.error(request, 'PDF can only be generated for approved payment forms')
        return redirect('vouchers:pf_detail', pk=pk)

    # Generate PDF using the Form PDF generator
    from .pdf_generator import FormPDFGenerator
    return FormPDFGenerator.generate_pdf(payment_form)


# ============================================================================
# REPORTS VIEWS
# ============================================================================

@login_required
def reports_view(request):
    """Display reports page with advanced filters and analytics"""
    from accounts.models import User
    from .models import Department
    from django.db.models import Sum, Count
    from collections import defaultdict
    from datetime import datetime, timedelta

    # Get approved documents only
    approved_vouchers = PaymentVoucher.objects.filter(status='APPROVED')
    approved_forms = PaymentForm.objects.filter(status='APPROVED')

    # Calculate totals by currency
    currency_totals = {'USD': 0, 'KHR': 0, 'THB': 0}
    for voucher in approved_vouchers:
        totals = voucher.calculate_grand_total()
        for currency, amount in totals.items():
            currency_totals[currency] += float(amount)

    for form in approved_forms:
        totals = form.calculate_grand_total()
        for currency, amount in totals.items():
            currency_totals[currency] += float(amount)

    # Monthly data for last 6 months
    monthly_data = defaultdict(lambda: {'PV': 0, 'PF': 0, 'amount': 0})
    six_months_ago = datetime.now() - timedelta(days=180)

    for voucher in approved_vouchers.filter(payment_date__gte=six_months_ago):
        month_key = voucher.payment_date.strftime('%Y-%m')
        monthly_data[month_key]['PV'] += 1
        totals = voucher.calculate_grand_total()
        monthly_data[month_key]['amount'] += float(totals.get('USD', 0))

    for form in approved_forms.filter(payment_date__gte=six_months_ago):
        month_key = form.payment_date.strftime('%Y-%m')
        monthly_data[month_key]['PF'] += 1
        totals = form.calculate_grand_total()
        monthly_data[month_key]['amount'] += float(totals.get('USD', 0))

    # Sort monthly data
    sorted_months = sorted(monthly_data.keys())

    context = {
        'users': User.objects.all().order_by('first_name', 'last_name'),
        'departments': Department.objects.filter(is_active=True).order_by('name'),
        'statuses': ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED'],
        'doc_types': ['PV', 'PF'],

        # Analytics data
        'total_approved': approved_vouchers.count() + approved_forms.count(),
        'total_pv': approved_vouchers.count(),
        'total_pf': approved_forms.count(),
        'total_usd': currency_totals['USD'],
        'total_khr': currency_totals['KHR'],
        'total_thb': currency_totals['THB'],
        'monthly_labels': sorted_months,
        'monthly_pv': [monthly_data[m]['PV'] for m in sorted_months],
        'monthly_pf': [monthly_data[m]['PF'] for m in sorted_months],
        'monthly_amounts': [monthly_data[m]['amount'] for m in sorted_months],
    }

    return render(request, 'vouchers/reports.html', context)


@login_required
def export_excel(request):
    """Export filtered vouchers/forms to Excel"""
    from .reports import ReportGenerator
    from django.http import HttpResponse

    # Get filter parameters
    filters = {
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
        'status': request.GET.get('status'),
        'creator': request.GET.get('creator'),
        'department': request.GET.get('department'),
        'payee_name': request.GET.get('payee_name'),
        'doc_type': request.GET.get('doc_type'),
    }

    # Generate report
    generator = ReportGenerator(filters)
    excel_file = generator.export_to_excel()

    # Return as download
    response = HttpResponse(
        excel_file,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="vouchers_report.xlsx"'

    return response


@login_required
def export_pdf(request):
    """Export filtered vouchers/forms to PDF"""
    from .reports import ReportGenerator
    from django.http import HttpResponse

    # Get filter parameters
    filters = {
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
        'status': request.GET.get('status'),
        'creator': request.GET.get('creator'),
        'department': request.GET.get('department'),
        'payee_name': request.GET.get('payee_name'),
        'doc_type': request.GET.get('doc_type'),
    }

    # Generate report
    generator = ReportGenerator(filters)
    pdf_file = generator.export_to_pdf()

    # Return as download
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vouchers_report.pdf"'

    return response