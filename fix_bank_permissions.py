#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fix: Grant company bank account permissions to users who need it
"""
import os
import sys
import django

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from accounts.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from vouchers.models import CompanyBankAccount

def grant_bank_permissions():
    print("=" * 70)
    print("GRANTING COMPANY BANK ACCOUNT PERMISSIONS")
    print("=" * 70)

    # Get the ContentType for CompanyBankAccount
    content_type = ContentType.objects.get_for_model(CompanyBankAccount)

    # Get all required permissions
    permissions = {
        'add': Permission.objects.get(codename='add_companybankaccount', content_type=content_type),
        'change': Permission.objects.get(codename='change_companybankaccount', content_type=content_type),
        'delete': Permission.objects.get(codename='delete_companybankaccount', content_type=content_type),
        'view': Permission.objects.get(codename='view_companybankaccount', content_type=content_type),
    }

    print("\nPermissions found:")
    for key, perm in permissions.items():
        print(f"  - {key}: {perm}")

    # Users who should have bank account permissions
    # Account Payable (role_level=1), Account Supervisor (role_level=2), Finance Manager (role_level=3)
    target_role_levels = [1, 2, 3]

    print(f"\n\nGranting permissions to users with role levels: {target_role_levels}")
    print("(Account Payable, Account Supervisor, Finance Manager)")
    print("-" * 70)

    users_updated = []

    for role_level in target_role_levels:
        users = User.objects.filter(role_level=role_level, is_staff=True)

        for user in users:
            print(f"\nUser: {user.username} ({user.get_role_level_display()})")

            # Check current permissions
            had_add = user.has_perm('vouchers.add_companybankaccount')

            # Grant all permissions
            for perm_name, perm in permissions.items():
                user.user_permissions.add(perm)

            # Check if actually granted
            now_has_add = user.has_perm('vouchers.add_companybankaccount')

            if not had_add and now_has_add:
                print(f"  ✓ Permissions granted!")
                users_updated.append(user.username)
            elif had_add:
                print(f"  → Already had permissions (refreshed)")
            else:
                print(f"  ⚠ Permission grant may have failed")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if users_updated:
        print(f"\n✓ Successfully granted bank account permissions to {len(users_updated)} user(s):")
        for username in users_updated:
            print(f"  - {username}")
    else:
        print("\n✓ All target users already had the necessary permissions")

    print("\nThese users can now:")
    print("  • Add new company bank accounts")
    print("  • Edit existing bank accounts")
    print("  • Delete bank accounts")
    print("  • View all bank accounts")

if __name__ == '__main__':
    try:
        grant_bank_permissions()
        print("\n✓ Permission update complete!")
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
