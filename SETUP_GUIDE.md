# Payment Voucher System - Setup & Testing Guide

## 🎉 System Status: READY FOR TESTING

All core features have been implemented and are ready to use!

---

## 📋 Quick Start Guide

### 1. Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 2. Run the Development Server

```bash
python manage.py runserver
```

The system will be available at: **http://localhost:8000**

---

## 🔧 Initial Setup

### Step 1: Create Test Users

1. Go to **http://localhost:8000/admin**
2. Login with your superuser credentials
3. Navigate to **Accounts > Users**
4. Create 5 test users with these role levels:

| Username | Role Level | Role Name |
|----------|-----------|-----------|
| officer1 | 1 | Account Payable |
| supervisor1 | 2 | Account Supervisor |
| manager1 | 3 | Finance Manager |
| gm1 | 4 | General Manager |
| md1 | 5 | Managing Director |

**For each user:**
- Set a simple password (e.g., "password123")
- Check "Email verified" checkbox
- Assign the appropriate Role Level
- Optionally upload a signature image

### Step 2: Verify Departments

Go to **Vouchers > Departments** in admin to verify these departments exist:
- Finance (FIN)
- Operations (OPS)
- Marketing (MKT)
- Human Resources (HR)
- Information Technology (IT)
- Maintenance (MNT)
- Administration (ADM)
- Customer Service (CS)

---

## 🧪 Complete Testing Workflow

### Test Scenario 1: Full Approval Chain (Without MD)

1. **Login as Account Payable (officer1)**
   - Go to: http://localhost:8000/accounts/login/
   - Create a new voucher (Dashboard → Create New Voucher)
   - Add payee details
   - Add 2-3 line items (try one with VAT checkbox)
   - Save voucher
   - Upload an attachment (optional)
   - Click "Submit for Approval"
   - **Verify**: PV Number generated (format: YYMM-0001)

2. **Login as Account Supervisor (supervisor1)**
   - Check Dashboard → "Pending My Action" shows the voucher
   - Click to view voucher details
   - Review details
   - Select "Approve" and submit
   - **Verify**: Email notification sent to Finance Manager

3. **Login as Finance Manager (manager1)**
   - View pending voucher
   - Approve the voucher
   - **Verify**: Email notification sent to General Manager

4. **Login as General Manager (gm1)**
   - View pending voucher
   - Select "Approve"
   - **Do NOT check** "Requires MD Approval"
   - Submit decision
   - **Verify**: Status changes to "APPROVED"
   - **Verify**: Email notification sent to officer1

5. **Login as Account Payable (officer1)**
   - Go to the approved voucher
   - Click "Download PDF"
   - **Verify**: PDF contains all signatures and timestamps

### Test Scenario 2: MD Approval Required

1. **Repeat steps 1-3 from Scenario 1**
2. **As General Manager (gm1):**
   - Select "Approve"
   - **CHECK** "Requires MD Approval" box
   - Submit
   - **Verify**: Status changes to "PENDING_L5"

3. **Login as Managing Director (md1)**
   - View and approve voucher
   - **Verify**: Status becomes "APPROVED"
   - Download PDF and verify MD signature appears

### Test Scenario 3: Return for Revision

1. **Create and submit a voucher (as officer1)**
2. **As Supervisor (supervisor1):**
   - Select "Return for Revision"
   - Add comments: "Please provide more details in line item 1"
   - Submit
   - **Verify**: Status = "ON_REVISION"
   - **Verify**: Email sent to officer1

3. **As Officer (officer1):**
   - View returned voucher
   - Click "Edit Voucher"
   - Update the details
   - Save and re-submit
   - **Verify**: New approval chain starts
   - **Verify**: Previous signatures cleared

### Test Scenario 4: Rejection

1. **Create and submit a voucher**
2. **As any approver:**
   - Select "Reject"
   - Add reason: "Incorrect payee information"
   - Submit
   - **Verify**: Status = "REJECTED"
   - **Verify**: Voucher is locked (cannot edit)
   - **Verify**: Email sent to creator

---

## 🔐 Security Features Implemented

✅ **Authentication & Authorization:**
- Email verification required
- Role-based access control (5 levels)
- Password validation
- Session management

✅ **Data Security:**
- CSRF protection (Django default)
- SQL injection prevention (Django ORM)
- XSS prevention (template auto-escaping)
- Secure file uploads with validation

✅ **Access Control:**
- Users can only view vouchers they're involved with
- Secure attachment downloads with permission checks
- Approved/Rejected vouchers are immutable
- Only assigned approvers can take actions

✅ **File Security:**
- File type validation (PNG, JPG, PDF only)
- File size limits (10MB max)
- MIME type checking
- Files stored in non-public directory

---

## 📊 Dashboard Features

**For Account Payables (Level 1):**
- Create new vouchers
- View "My Vouchers"
- Edit draft/on-revision vouchers
- Upload attachments
- Submit for approval

**For Approvers (Levels 2-5):**
- View "Pending My Action"
- Approve vouchers
- Reject vouchers
- Return for revision
- Add comments

**For All Users:**
- Dashboard with summary cards
- Filter vouchers by status
- View approval history
- Download approved PDFs

---

## 📧 Email Notifications

Emails are sent for:
1. **New submission** → Next approver
2. **Approval** → Next approver (or creator if final)
3. **Rejection** → Creator
4. **Return for revision** → Creator

**Note**: Configure Gmail SMTP in `.env` file:
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
```

---

## 📁 File Structure

```
PaymentVoucherSystem/
├── accounts/           # User authentication & roles
├── vouchers/          # Voucher CRUD & PDF generation
├── workflow/          # State machine & notifications
├── dashboard/         # Dashboard & list views
├── templates/         # HTML templates
├── static/           # CSS, JavaScript
├── media/            # Uploaded files & signatures
└── docs/             # Documentation (TRD)
```

---

## 🔄 Workflow Summary

```
DRAFT → Submit → PENDING_L2 (Supervisor)
                       ↓
                  PENDING_L3 (Finance Mgr)
                       ↓
                  PENDING_L4 (GM)
                       ↓
            ┌──────────┴──────────┐
      No MD Required        MD Required
            ↓                     ↓
        APPROVED            PENDING_L5 (MD)
                                  ↓
                              APPROVED

At any PENDING stage:
- REJECT → REJECTED (locked)
- RETURN → ON_REVISION → Edit → Re-submit
```

---

## 🎯 Key Features Verification Checklist

- [ ] User registration with email verification
- [ ] 5-level role-based access
- [ ] Digital signature upload
- [ ] Create vouchers with dynamic line items
- [ ] VAT calculation (10% Cambodia)
- [ ] File attachments (PNG, JPG, PDF)
- [ ] Auto-generated PV numbers (YYMM-NNNN)
- [ ] Submit vouchers for approval
- [ ] Approve/Reject/Return workflow
- [ ] GM decision on MD approval requirement
- [ ] Email notifications at each stage
- [ ] PDF generation with signatures & timestamps
- [ ] Approval history tracking
- [ ] Dashboard with filters
- [ ] Access control & security
- [ ] Immutability of approved/rejected vouchers

---

## 🚀 Production Deployment

When ready for production:

1. **Update `.env` file:**
   ```
   DEBUG=False
   USE_SQLITE=False  # Switch to PostgreSQL
   ```

2. **Install PostgreSQL dependencies:**
   ```bash
   pip install psycopg[binary]>=3.1.0
   ```

3. **Create PostgreSQL database:**
   ```sql
   CREATE DATABASE payment_voucher_system;
   CREATE USER pvs_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE payment_voucher_system TO pvs_user;
   ```

4. **Run migrations on production:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   python manage.py populate_departments
   ```

5. **Set up Gunicorn + Nginx** (see README.md for details)

---

## 📞 Support

For issues or questions, refer to:
- `README.md` - General documentation
- `docs/TRD Payment Voucher System.pdf` - Technical requirements
- Django Admin: http://localhost:8000/admin

---

## ✅ System Status

**All 8 Implementation Phases Complete:**
1. ✅ Foundation & Setup
2. ✅ User Authentication
3. ✅ Voucher Models
4. ✅ Workflow Engine
5. ✅ Voucher CRUD
6. ✅ Dashboard
7. ✅ PDF Generation
8. ✅ Security Hardening

**The Payment Voucher System is ready for testing and deployment!** 🎉
