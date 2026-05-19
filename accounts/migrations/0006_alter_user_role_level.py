# Generated migration for Finance Controller role addition

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_user_role_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role_level',
            field=models.IntegerField(blank=True, choices=[(1, 'Account Payable'), (2, 'Account Supervisor'), (3, 'Finance Manager'), (4, 'Finance Controller'), (5, 'General Manager'), (6, 'Managing Director'), (99, 'System Admin')], help_text="User's role level in the approval chain", null=True),
        ),
    ]
