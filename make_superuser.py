#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Make a user a superuser so they can manage bank accounts
"""
import os
import sys
import django

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from accounts.models import User

def make_superuser():
    print("=" * 70)
    print("MAKE USER SUPERUSER")
    print("=" * 70)

    print("\nAvailable non-superuser staff:")
    non_super = User.objects.filter(is_staff=True, is_superuser=False)

    for user in non_super:
        print(f"  - {user.username} ({user.get_role_level_display()})")

    if not non_super.exists():
        print("  No non-superuser staff found")
        return

    print("\n" + "-" * 70)
    username = input("\nEnter username to make superuser (or press Enter to cancel): ").strip()

    if not username:
        print("Cancelled.")
        return

    try:
        user = User.objects.get(username=username)

        if user.is_superuser:
            print(f"\n{username} is already a superuser!")
            return

        # Make superuser
        user.is_superuser = True
        user.save()

        print(f"\n✓ SUCCESS: {username} is now a superuser!")
        print(f"\nThey can now:")
        print(f"  • Add/Edit/Delete company bank accounts")
        print(f"  • Access all admin features")
        print(f"  • Manage other users")

    except User.DoesNotExist:
        print(f"\n✗ ERROR: User '{username}' not found")

if __name__ == '__main__':
    try:
        make_superuser()
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
