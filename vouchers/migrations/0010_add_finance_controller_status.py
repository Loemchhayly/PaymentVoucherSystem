# Generated migration for Finance Controller status addition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vouchers', '0009_alter_companybankaccount_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentvoucher',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PENDING_L2', 'Pending Account Supervisor'),
                    ('PENDING_L3', 'Pending Finance Manager'),
                    ('PENDING_L4', 'Pending Finance Controller'),
                    ('PENDING_L5', 'Pending General Manager'),
                    ('PENDING_L6', 'Pending Managing Director'),
                    ('ON_REVISION', 'On Revision'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='paymentform',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('PENDING_L2', 'Pending Account Supervisor'),
                    ('PENDING_L3', 'Pending Finance Manager'),
                    ('PENDING_L4', 'Pending Finance Controller'),
                    ('PENDING_L5', 'Pending General Manager'),
                    ('PENDING_L6', 'Pending Managing Director'),
                    ('ON_REVISION', 'On Revision'),
                    ('APPROVED', 'Approved'),
                    ('REJECTED', 'Rejected'),
                ],
                default='DRAFT',
                max_length=20,
            ),
        ),
    ]
