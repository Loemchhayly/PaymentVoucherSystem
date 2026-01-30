"""
Test script for PV number attachment storage
Run with: python manage.py shell < test_pv_attachments.py
"""
from vouchers.models import PaymentVoucher, VoucherAttachment
from accounts.models import User
from django.core.files.base import ContentFile
from django.utils import timezone
import os

print("=" * 70)
print("PV NUMBER ATTACHMENT STORAGE TEST")
print("=" * 70)
print()

# Test 1: Check if PV number is generated on voucher creation
print("TEST 1: PV Number Generation on Creation")
print("-" * 70)

# Get a test user
user = User.objects.filter(is_active=True, role_level=1).first()
if not user:
    print("[ERROR] No active user found with role_level=1")
    print("Please create a test user first")
    exit(1)

print(f"Using test user: {user.username}")

# Create a test voucher (simulating the view logic)
from workflow.state_machine import VoucherStateMachine

# First create voucher instance without saving
voucher = PaymentVoucher(
    created_by=user,
    payee_name="Test Payee",
    payment_date=timezone.now().date(),
    bank_name="Test Bank",
    bank_account="123456789"
)

# Generate PV number using payment_date
voucher.pv_number = VoucherStateMachine.generate_pv_number(voucher)

# Now save the voucher
voucher.save()

print(f"[OK] Voucher created with ID: {voucher.id}")
print(f"[OK] PV Number assigned: {voucher.pv_number}")
print(f"[OK] Status: {voucher.status}")
print()

# Test 2: Check attachment upload path
print("TEST 2: Attachment Upload Path")
print("-" * 70)

# Create a test file
test_content = b"This is a test PDF file content"
test_file = ContentFile(test_content, name="test_invoice.pdf")

# Create attachment
attachment = VoucherAttachment.objects.create(
    voucher=voucher,
    file=test_file,
    filename="test_invoice.pdf",
    file_size=len(test_content),
    uploaded_by=user
)

print(f"[OK] Attachment created with ID: {attachment.id}")
print(f"[OK] Filename: {attachment.filename}")
print(f"[OK] File path: {attachment.file.name}")
print(f"[OK] Expected path: voucher_attachments/{voucher.pv_number}/test_invoice.pdf")

# Verify path format
expected_path = f"voucher_attachments/{voucher.pv_number}/test_invoice.pdf"
if attachment.file.name == expected_path:
    print("[OK] ✓ Path format is CORRECT!")
else:
    print(f"[WARNING] ✗ Path mismatch!")
    print(f"           Expected: {expected_path}")
    print(f"           Got:      {attachment.file.name}")

print()

# Test 3: Check voucher methods
print("TEST 3: Voucher Methods")
print("-" * 70)

folder_path = voucher.get_attachment_folder()
print(f"[OK] get_attachment_folder() returns: {folder_path}")
print(f"[OK] Expected: voucher_attachments/{voucher.pv_number}")

if folder_path == f"voucher_attachments/{voucher.pv_number}":
    print("[OK] ✓ Folder path is CORRECT!")
else:
    print(f"[WARNING] ✗ Folder path mismatch!")

print()

# Test 4: Multiple attachments in same folder
print("TEST 4: Multiple Attachments in Same Folder")
print("-" * 70)

# Create second attachment
test_file2 = ContentFile(b"Second test file", name="test_receipt.jpg")
attachment2 = VoucherAttachment.objects.create(
    voucher=voucher,
    file=test_file2,
    filename="test_receipt.jpg",
    file_size=16,
    uploaded_by=user
)

print(f"[OK] Second attachment created: {attachment2.filename}")
print(f"[OK] File path: {attachment2.file.name}")

# Extract folder from both attachments
folder1 = os.path.dirname(attachment.file.name)
folder2 = os.path.dirname(attachment2.file.name)

print(f"[OK] Attachment 1 folder: {folder1}")
print(f"[OK] Attachment 2 folder: {folder2}")

if folder1 == folder2:
    print("[OK] ✓ Both attachments in SAME folder!")
else:
    print("[WARNING] ✗ Attachments in DIFFERENT folders!")

print()

# Test 5: DRAFT voucher without PV number
print("TEST 5: DRAFT Voucher Fallback")
print("-" * 70)

# Create voucher without PV number
draft_voucher = PaymentVoucher.objects.create(
    created_by=user,
    payee_name="Draft Test",
    payment_date=timezone.now().date(),
    bank_name="Test Bank",
    bank_account="987654321",
    # pv_number left as None
)

print(f"[OK] Draft voucher created with ID: {draft_voucher.id}")
print(f"[OK] PV Number: {draft_voucher.pv_number} (should be None)")

# Check folder path
draft_folder = draft_voucher.get_attachment_folder()
print(f"[OK] get_attachment_folder() returns: {draft_folder}")
print(f"[OK] Expected: voucher_attachments/DRAFT-{draft_voucher.id}")

if draft_folder == f"voucher_attachments/DRAFT-{draft_voucher.id}":
    print("[OK] ✓ DRAFT fallback is CORRECT!")
else:
    print(f"[WARNING] ✗ DRAFT fallback mismatch!")

# Create attachment for draft voucher
test_file3 = ContentFile(b"Draft attachment", name="draft_doc.pdf")
attachment3 = VoucherAttachment.objects.create(
    voucher=draft_voucher,
    file=test_file3,
    filename="draft_doc.pdf",
    file_size=16,
    uploaded_by=user
)

print(f"[OK] Draft attachment path: {attachment3.file.name}")
expected_draft_path = f"voucher_attachments/DRAFT-{draft_voucher.id}/draft_doc.pdf"
if attachment3.file.name == expected_draft_path:
    print("[OK] ✓ Draft attachment path is CORRECT!")
else:
    print(f"[WARNING] ✗ Draft path mismatch!")

print()

# Summary
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("[OK] All tests completed!")
print()
print("Test vouchers created:")
print(f"  - Voucher ID {voucher.id} with PV: {voucher.pv_number}")
print(f"  - Draft Voucher ID {draft_voucher.id} (no PV)")
print()
print("To clean up test data, run:")
print(f"  PaymentVoucher.objects.filter(id__in=[{voucher.id}, {draft_voucher.id}]).delete()")
print()
print("=" * 70)
