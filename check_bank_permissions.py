#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Check why user can't add more company bank accounts
"""
import os
import sys
import django

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PaymentVoucherSystem.settings')
django.setup()

from accounts.models import User
from vouchers.models import CompanyBankAccount, CAMBODIAN_BANKS

def check_bank_accounts():
    print("=" * 70)
    print("COMPANY BANK ACCOUNT DIAGNOSTIC")
    print("=" * 70)

    # Show existing accounts
    print("\n1. EXISTING BANK ACCOUNTS")
    print("-" * 70)
    accounts = CompanyBankAccount.objects.all()
    print(f"Total accounts: {accounts.count()}")

    for i, acc in enumerate(accounts, 1):
        print(f"\n  {i}. {acc.company_name}")
        print(f"     Bank: {acc.bank}")
        print(f"     Account Number: {acc.account_number}")
        print(f"     Currency: {acc.currency}")
        print(f"     Active: {acc.is_active}")

    # Show available banks
    print("\n2. AVAILABLE BANKS IN SYSTEM")
    print("-" * 70)
    for code, name in CAMBODIAN_BANKS:
        existing = accounts.filter(bank=code).count()
        print(f"  • {name}")
        if existing > 0:
            print(f"    → {existing} account(s) already exist")
        else:
            print(f"    → ✓ No accounts yet (can add)")

    # Check user permissions
    print("\n3. USER PERMISSIONS CHECK")
    print("-" * 70)

    # Check all staff users
    staff_users = User.objects.filter(is_staff=True)
    print(f"Staff users: {staff_users.count()}")

    for user in staff_users:
        print(f"\n  User: {user.username} ({user.get_role_level_display() if hasattr(user, 'get_role_level_display') else 'Unknown'})")
        print(f"    is_staff: {user.is_staff}")
        print(f"    is_superuser: {user.is_superuser}")

        # Check specific permissions
        can_add = user.has_perm('vouchers.add_companybankaccount')
        can_change = user.has_perm('vouchers.change_companybankaccount')
        can_delete = user.has_perm('vouchers.delete_companybankaccount')
        can_view = user.has_perm('vouchers.view_companybankaccount')

        print(f"    Permissions:")
        print(f"      - Add bank account: {'✓ YES' if can_add else '✗ NO'}")
        print(f"      - Change bank account: {'✓ YES' if can_change else '✗ NO'}")
        print(f"      - Delete bank account: {'✓ YES' if can_delete else '✗ NO'}")
        print(f"      - View bank account: {'✓ YES' if can_view else '✗ NO'}")

    # Check unique constraints
    print("\n4. UNIQUE CONSTRAINT CHECK")
    print("-" * 70)
    print("The model has: unique_together = [['account_number', 'bank']]")
    print("This means:")
    print("  ✓ You CAN add multiple accounts to the same bank (different account numbers)")
    print("  ✓ You CAN add the same account number to different banks")
    print("  ✗ You CANNOT add the same account number to the same bank twice")

    # Check for duplicates
    print("\n5. DUPLICATE CHECK")
    print("-" * 70)
    from django.db.models import Count
    duplicates = CompanyBankAccount.objects.values('account_number', 'bank').annotate(
        count=Count('id')
    ).filter(count__gt=1)

    if duplicates.exists():
        print("⚠ WARNING: Found duplicate accounts:")
        for dup in duplicates:
            print(f"  - Account {dup['account_number']} at {dup['bank']} ({dup['count']} times)")
    else:
        print("✓ No duplicates found")

    # Summary and recommendations
    print("\n" + "=" * 70)
    print("SUMMARY & TROUBLESHOOTING")
    print("=" * 70)
    print("\nYou should be able to add more bank accounts if:")
    print("  1. ✓ You are logged in as a staff/superuser")
    print("  2. ✓ You have 'add_companybankaccount' permission")
    print("  3. ✓ The account number + bank combination doesn't already exist")
    print("\nCommon issues:")
    print("  • ERROR: 'Account with this Account number and Bank already exists'")
    print("    → You're trying to add a duplicate account number to the same bank")
    print("    → Use a different account number or different bank")
    print("\n  • ERROR: Permission denied")
    print("    → Login as superuser or get 'add_companybankaccount' permission")
    print("\n  • Can't see 'Add' button in admin")
    print("    → Check if you're logged in as staff user")
    print("    → Check you have permission to add bank accounts")

    print("\n" + "=" * 70)
    print("HOW TO ADD A NEW BANK ACCOUNT")
    print("=" * 70)
    print("\n1. Go to Django Admin: /admin/")
    print("2. Navigate to: VOUCHERS → Company bank accounts")
    print("3. Click 'ADD COMPANY BANK ACCOUNT' button (top right)")
    print("4. Fill in the form:")
    print("   - Company name: e.g., 'Phat Phnom Penh Co.,Ltd'")
    print("   - Account number: e.g., '123-456-789' (must be unique per bank)")
    print("   - Currency: USD, KHR, or THB")
    print("   - Bank: Choose from dropdown (ABA, ACLEDA, MAYBANK, etc.)")
    print("   - Is active: ✓ (checked)")
    print("5. Click 'SAVE'")
    print("\nIf you get an error, note the exact error message and let me know!")

if __name__ == '__main__':
    try:
        check_bank_accounts()
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
