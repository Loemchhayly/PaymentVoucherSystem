from django.utils import timezone
from django.db import transaction
from django.db.models import Max
from vouchers.models import PaymentVoucher, PaymentForm
from .models import ApprovalHistory, FormApprovalHistory
from django.contrib.auth import get_user_model

User = get_user_model()


class VoucherStateMachine:
    """
    Manages voucher state transitions and workflow logic.

    State Flow:
    DRAFT → [submit] → PENDING_L2 → [approve] → PENDING_L3 → [approve] → PENDING_L4
    → [approve with requires_md=False] → APPROVED
    → [approve with requires_md=True] → PENDING_L5 → [approve] → APPROVED

    At any PENDING_L* stage: [reject] → REJECTED or [return] → ON_REVISION
    ON_REVISION → [submit] → PENDING_L2 (starts new approval chain)
    """

    STATE_TRANSITIONS = {
        'DRAFT': {
            'submit': 'PENDING_L2',
        },
        'PENDING_L2': {
            'approve': 'PENDING_L3',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L3': {
            'approve': 'PENDING_L4',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L4': {
            'approve': None,  # Dynamic: PENDING_L5 if requires_md_approval, else APPROVED
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L5': {
            'approve': 'APPROVED',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'ON_REVISION': {
            'submit': 'PENDING_L2',
        },
        'APPROVED': {},  # Final state
        'REJECTED': {},  # Final state
    }

    ROLE_TO_STATUS = {
        2: 'PENDING_L2',
        3: 'PENDING_L3',
        4: 'PENDING_L4',
        5: 'PENDING_L5',
    }

    @classmethod
    def can_transition(cls, voucher, action, user):
        """
        Check if user can perform action on voucher.

        Returns: (bool, str) - (can_perform, error_message)
        """
        # Check if transition exists
        if action not in cls.STATE_TRANSITIONS.get(voucher.status, {}):
            return False, f"Action '{action}' not allowed for status '{voucher.get_status_display()}'"

        # Check user permissions
        if action == 'submit':
            # Only creator can submit
            if user != voucher.created_by:
                return False, "Only the creator can submit this voucher"
        else:
            # For approve/reject/return actions
            if voucher.current_approver != user:
                return False, "You are not the assigned approver for this voucher"

            # Verify user has correct role level
            expected_level = cls._get_level_from_status(voucher.status)
            if expected_level and user.role_level != expected_level:
                return False, f"Your role level ({user.role_level}) does not match required level ({expected_level})"

        return True, None

    @classmethod
    @transaction.atomic
    def transition(cls, voucher, action, user, comments=''):
        """
        Execute state transition.

        Args:
            voucher: PaymentVoucher instance
            action: str - 'submit', 'approve', 'reject', 'return'
            user: User instance
            comments: str - optional comments

        Returns:
            PaymentVoucher instance (updated)

        Raises:
            ValueError: if transition is not allowed
        """
        # Validate transition
        can_do, error = cls.can_transition(voucher, action, user)
        if not can_do:
            raise ValueError(error)

        # Prevent duplicate approvals from the same user
        if action == 'approve':
            existing_approval = voucher.approval_history.filter(
                actor=user,
                action='APPROVE'
            ).exists()
            if existing_approval:
                raise ValueError(f"{user.get_full_name() or user.username} has already approved this voucher")

        # Get next state
        next_state = cls.STATE_TRANSITIONS[voucher.status][action]

        # Handle dynamic state for GM approval
        if voucher.status == 'PENDING_L4' and action == 'approve':
            next_state = 'PENDING_L5' if voucher.requires_md_approval else 'APPROVED'

        # Handle special cases
        if action == 'return':
            # Clear all approval signatures when returned for revision
            voucher.approval_history.filter(action='APPROVE').delete()

        if action == 'submit':
            if voucher.status == 'DRAFT':
                # First submission - ensure PV number exists
                if not voucher.pv_number:
                    voucher.pv_number = cls.generate_pv_number(voucher)
                voucher.submitted_at = timezone.now()
            elif voucher.status == 'ON_REVISION':
                # Resubmission after revision
                voucher.submitted_at = timezone.now()

        # Update voucher state
        old_status = voucher.status
        voucher.status = next_state
        voucher.current_approver = cls.get_next_approver(next_state)
        voucher.save()

        # Copy signature image if approving
        signature_image = None
        if action == 'approve' and user.signature_image:
            signature_image = user.signature_image

        # Record in history
        ApprovalHistory.objects.create(
            voucher=voucher,
            action=action.upper(),
            actor=user,
            actor_role_level=user.role_level or 0,
            comments=comments,
            signature_image=signature_image
        )

        # Send notifications (import here to avoid circular import)
        from .services import NotificationService
        NotificationService.send_notification(voucher, action, user, comments)

        return voucher

    @staticmethod
    def generate_pv_number(voucher):
        """
        Generate unique PV number in format YYMM-NNNN.
        Counter resets every month based on payment date.

        Args:
            voucher: PaymentVoucher instance (to get payment_date)
        """
        # Use payment date instead of current date for numbering
        prefix = voucher.payment_date.strftime('%y%m')

        # Get last number for this payment month
        last_pv = PaymentVoucher.objects.filter(
            pv_number__startswith=prefix
        ).aggregate(Max('pv_number'))['pv_number__max']

        if last_pv:
            # Extract number part and increment
            last_num = int(last_pv.split('-')[1])
            next_num = last_num + 1
        else:
            # First voucher of the month
            next_num = 1

        return f"{prefix}-{next_num:04d}"

    @staticmethod
    def generate_pf_number(payment_form):
        """
        Generate unique PF number in format YYMM-PF-NNNN.
        Counter resets every month based on payment date.

        Args:
            payment_form: PaymentForm instance (to get payment_date)
        """
        # Use payment date instead of current date for numbering
        prefix = payment_form.payment_date.strftime('%y%m')

        # Get last number for this payment month (PF numbers include '-PF-' in format)
        last_pf = PaymentForm.objects.filter(
            pf_number__startswith=f"{prefix}-PF"
        ).aggregate(Max('pf_number'))['pf_number__max']

        if last_pf:
            # Extract number part and increment (format: YYMM-PF-NNNN)
            last_num = int(last_pf.split('-')[2])
            next_num = last_num + 1
        else:
            # First form of the month
            next_num = 1

        return f"{prefix}-PF-{next_num:04d}"

    @staticmethod
    def get_next_approver(status):
        """
        Get next approver based on status.
        Returns first available user with required role level.
        """
        role_map = {
            'PENDING_L2': 2,
            'PENDING_L3': 3,
            'PENDING_L4': 4,
            'PENDING_L5': 5,
        }

        if status not in role_map:
            return None

        required_level = role_map[status]

        # Get first active, verified, and approved user with required role level
        return User.objects.filter(
            role_level=required_level,
            is_active=True,
            email_verified=True,
            is_approved=True  # User must be approved by admin
        ).first()

    @staticmethod
    def _get_level_from_status(status):
        """Helper to get role level from status"""
        level_map = {
            'PENDING_L2': 2,
            'PENDING_L3': 3,
            'PENDING_L4': 4,
            'PENDING_L5': 5,
        }
        return level_map.get(status)


class FormStateMachine:
    """
    Manages payment form state transitions and workflow logic.

    State Flow:
    DRAFT → [submit] → PENDING_L2 → [approve] → PENDING_L3 → [approve] → PENDING_L4
    → [approve with requires_md=False] → APPROVED
    → [approve with requires_md=True] → PENDING_L5 → [approve] → APPROVED

    At any PENDING_L* stage: [reject] → REJECTED or [return] → ON_REVISION
    ON_REVISION → [submit] → PENDING_L2 (starts new approval chain)
    """

    STATE_TRANSITIONS = {
        'DRAFT': {
            'submit': 'PENDING_L2',
        },
        'PENDING_L2': {
            'approve': 'PENDING_L3',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L3': {
            'approve': 'PENDING_L4',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L4': {
            'approve': None,  # Dynamic: PENDING_L5 if requires_md_approval, else APPROVED
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'PENDING_L5': {
            'approve': 'APPROVED',
            'reject': 'REJECTED',
            'return': 'ON_REVISION',
        },
        'ON_REVISION': {
            'submit': 'PENDING_L2',
        },
        'APPROVED': {},  # Final state
        'REJECTED': {},  # Final state
    }

    ROLE_TO_STATUS = {
        2: 'PENDING_L2',
        3: 'PENDING_L3',
        4: 'PENDING_L4',
        5: 'PENDING_L5',
    }

    @classmethod
    def can_transition(cls, payment_form, action, user):
        """
        Check if user can perform action on payment form.

        Returns: (bool, str) - (can_perform, error_message)
        """
        # Check if transition exists
        if action not in cls.STATE_TRANSITIONS.get(payment_form.status, {}):
            return False, f"Action '{action}' not allowed for status '{payment_form.get_status_display()}'"

        # Check user permissions
        if action == 'submit':
            # Only creator can submit
            if user != payment_form.created_by:
                return False, "Only the creator can submit this form"
        else:
            # For approve/reject/return actions
            if payment_form.current_approver != user:
                return False, "You are not the assigned approver for this form"

            # Verify user has correct role level
            expected_level = cls._get_level_from_status(payment_form.status)
            if expected_level and user.role_level != expected_level:
                return False, f"Your role level ({user.role_level}) does not match required level ({expected_level})"

        return True, None

    @classmethod
    @transaction.atomic
    def transition(cls, payment_form, action, user, comments=''):
        """
        Execute state transition.

        Args:
            payment_form: PaymentForm instance
            action: str - 'submit', 'approve', 'reject', 'return'
            user: User instance
            comments: str - optional comments

        Returns:
            PaymentForm instance (updated)

        Raises:
            ValueError: if transition is not allowed
        """
        # Validate transition
        can_do, error = cls.can_transition(payment_form, action, user)
        if not can_do:
            raise ValueError(error)

        # Prevent duplicate approvals from the same user
        if action == 'approve':
            existing_approval = payment_form.approval_history.filter(
                actor=user,
                action='APPROVE'
            ).exists()
            if existing_approval:
                raise ValueError(f"{user.get_full_name() or user.username} has already approved this form")

        # Get next state
        next_state = cls.STATE_TRANSITIONS[payment_form.status][action]

        # Handle dynamic state for GM approval
        if payment_form.status == 'PENDING_L4' and action == 'approve':
            next_state = 'PENDING_L5' if payment_form.requires_md_approval else 'APPROVED'

        # Handle special cases
        if action == 'return':
            # Clear all approval signatures when returned for revision
            payment_form.approval_history.filter(action='APPROVE').delete()

        if action == 'submit':
            if payment_form.status == 'DRAFT':
                # First submission - ensure PF number exists
                if not payment_form.pf_number:
                    payment_form.pf_number = VoucherStateMachine.generate_pf_number(payment_form)
                payment_form.submitted_at = timezone.now()
            elif payment_form.status == 'ON_REVISION':
                # Resubmission after revision
                payment_form.submitted_at = timezone.now()

        # Update form state
        old_status = payment_form.status
        payment_form.status = next_state
        payment_form.current_approver = cls.get_next_approver(next_state)
        payment_form.save()

        # Copy signature image if approving
        signature_image = None
        if action == 'approve' and user.signature_image:
            signature_image = user.signature_image

        # Record in history
        FormApprovalHistory.objects.create(
            payment_form=payment_form,
            action=action.upper(),
            actor=user,
            actor_role_level=user.role_level or 0,
            comments=comments,
            signature_image=signature_image
        )

        # Send notifications (import here to avoid circular import)
        from .services import NotificationService
        NotificationService.send_notification(payment_form, action, user, comments)

        return payment_form

    @staticmethod
    def get_next_approver(status):
        """
        Get next approver based on status.
        Returns first available user with required role level.
        """
        role_map = {
            'PENDING_L2': 2,
            'PENDING_L3': 3,
            'PENDING_L4': 4,
            'PENDING_L5': 5,
        }

        if status not in role_map:
            return None

        required_level = role_map[status]

        # Get first active, verified, and approved user with required role level
        return User.objects.filter(
            role_level=required_level,
            is_active=True,
            email_verified=True,
            is_approved=True  # User must be approved by admin
        ).first()

    @staticmethod
    def _get_level_from_status(status):
        """Helper to get role level from status"""
        level_map = {
            'PENDING_L2': 2,
            'PENDING_L3': 3,
            'PENDING_L4': 4,
            'PENDING_L5': 5,
        }
        return level_map.get(status)
