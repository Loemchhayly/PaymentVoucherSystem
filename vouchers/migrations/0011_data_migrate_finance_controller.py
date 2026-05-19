# Data migration: renumber roles and statuses for Finance Controller insertion
# Old: 4=GM, 5=MD  →  New: 4=FC(new), 5=GM(was 4), 6=MD(was 5)

from django.db import migrations


def upgrade_roles_and_statuses(apps, schema_editor):
    """
    Migrate existing data:
    - User role_level: 5 → 6 (MD), then 4 → 5 (GM)
    - PaymentVoucher status: PENDING_L5 → PENDING_L6, then PENDING_L4 → PENDING_L5
    - PaymentForm status: same
    - ApprovalHistory actor_role_level: 5 → 6, then 4 → 5
    - FormApprovalHistory actor_role_level: 5 → 6, then 4 → 5
    - revision_return_level on both models: 5 → 6, then 4 → 5
    """
    User = apps.get_model('accounts', 'User')
    PaymentVoucher = apps.get_model('vouchers', 'PaymentVoucher')
    PaymentForm = apps.get_model('vouchers', 'PaymentForm')

    # We need to import workflow models
    ApprovalHistory = apps.get_model('workflow', 'ApprovalHistory')
    FormApprovalHistory = apps.get_model('workflow', 'FormApprovalHistory')

    # ── Users: role_level 5 → 6 (MD), then 4 → 5 (GM) ──
    User.objects.filter(role_level=5).update(role_level=6)
    User.objects.filter(role_level=4).update(role_level=5)

    # ── PaymentVoucher status ──
    PaymentVoucher.objects.filter(status='PENDING_L5').update(status='PENDING_L6')
    PaymentVoucher.objects.filter(status='PENDING_L4').update(status='PENDING_L5')

    # ── PaymentForm status ──
    PaymentForm.objects.filter(status='PENDING_L5').update(status='PENDING_L6')
    PaymentForm.objects.filter(status='PENDING_L4').update(status='PENDING_L5')

    # ── ApprovalHistory actor_role_level ──
    ApprovalHistory.objects.filter(actor_role_level=5).update(actor_role_level=6)
    ApprovalHistory.objects.filter(actor_role_level=4).update(actor_role_level=5)

    # ── FormApprovalHistory actor_role_level ──
    FormApprovalHistory.objects.filter(actor_role_level=5).update(actor_role_level=6)
    FormApprovalHistory.objects.filter(actor_role_level=4).update(actor_role_level=5)

    # ── PaymentVoucher revision_return_level ──
    PaymentVoucher.objects.filter(revision_return_level=5).update(revision_return_level=6)
    PaymentVoucher.objects.filter(revision_return_level=4).update(revision_return_level=5)

    # ── PaymentForm revision_return_level ──
    PaymentForm.objects.filter(revision_return_level=5).update(revision_return_level=6)
    PaymentForm.objects.filter(revision_return_level=4).update(revision_return_level=5)


def downgrade_roles_and_statuses(apps, schema_editor):
    """Reverse the migration"""
    User = apps.get_model('accounts', 'User')
    PaymentVoucher = apps.get_model('vouchers', 'PaymentVoucher')
    PaymentForm = apps.get_model('vouchers', 'PaymentForm')
    ApprovalHistory = apps.get_model('workflow', 'ApprovalHistory')
    FormApprovalHistory = apps.get_model('workflow', 'FormApprovalHistory')

    # Reverse: 5 → 4 (GM back), then 6 → 5 (MD back)
    User.objects.filter(role_level=5).update(role_level=4)
    User.objects.filter(role_level=6).update(role_level=5)

    PaymentVoucher.objects.filter(status='PENDING_L5').update(status='PENDING_L4')
    PaymentVoucher.objects.filter(status='PENDING_L6').update(status='PENDING_L5')

    PaymentForm.objects.filter(status='PENDING_L5').update(status='PENDING_L4')
    PaymentForm.objects.filter(status='PENDING_L6').update(status='PENDING_L5')

    ApprovalHistory.objects.filter(actor_role_level=5).update(actor_role_level=4)
    ApprovalHistory.objects.filter(actor_role_level=6).update(actor_role_level=5)

    FormApprovalHistory.objects.filter(actor_role_level=5).update(actor_role_level=4)
    FormApprovalHistory.objects.filter(actor_role_level=6).update(actor_role_level=5)

    PaymentVoucher.objects.filter(revision_return_level=5).update(revision_return_level=4)
    PaymentVoucher.objects.filter(revision_return_level=6).update(revision_return_level=5)

    PaymentForm.objects.filter(revision_return_level=5).update(revision_return_level=4)
    PaymentForm.objects.filter(revision_return_level=6).update(revision_return_level=5)


class Migration(migrations.Migration):

    dependencies = [
        ('vouchers', '0010_add_finance_controller_status'),
        ('accounts', '0006_alter_user_role_level'),
        ('workflow', '0004_remove_backuphistory_workflow_ba_created_5996ca_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            upgrade_roles_and_statuses,
            downgrade_roles_and_statuses,
        ),
    ]
