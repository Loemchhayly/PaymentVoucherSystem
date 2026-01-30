# Payment Voucher System

A Django-based web application for managing payment voucher approvals with a 5-level workflow system.

## Features

- 5-level approval workflow (Account Payable → Account Supervisor → Finance Manager → General Manager → Managing Director)
- Auto-generated PV numbers (YYMM-NNNN format, resets monthly)
- Email notifications at each approval stage
- PDF generation with digital signatures
- Secure file attachments
- Dashboard with advanced filters
- Role-based access control

## Tech Stack

- **Backend**: Django 6.0.1 (Python)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML, Bootstrap 5, JavaScript
- **PDF Generation**: WeasyPrint
- **Email**: Gmail SMTP

## Initial Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
.\env\Scripts\activate  # Windows
# source env/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit the `.env` file with your settings:
- Email credentials (Gmail App Password)
- Database settings (if using PostgreSQL)

### 3. Create Database

Migrations have already been run. To reset:
```bash
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 5. Run Development Server

```bash
python manage.py runserver
```

Access the application at: http://localhost:8000

## Admin Setup

1. Go to http://localhost:8000/admin
2. Login with superuser credentials
3. Create 5 test users (one for each role level):
   - User 1: Account Payable (role_level=1)
   - User 2: Account Supervisor (role_level=2)
   - User 3: Finance Manager (role_level=3)
   - User 4: General Manager (role_level=4)
   - User 5: Managing Director (role_level=5)
4. Upload signature images for each user

## Database Configuration

### Development (SQLite)
Set in `.env`:
```
USE_SQLITE=True
```

### Production (PostgreSQL)
Set in `.env`:
```
USE_SQLITE=False
DB_NAME=payment_voucher_system
DB_USER=pvs_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Then install PostgreSQL adapter:
```bash
pip install psycopg[binary]>=3.1.0
```

## Project Structure

```
PaymentVoucherSystem/
├── accounts/          # User authentication and roles
├── vouchers/          # Voucher CRUD and management
├── workflow/          # Approval state machine
├── dashboard/         # Dashboard and reports
├── templates/         # HTML templates
├── static/           # CSS, JavaScript, images
├── media/            # User uploads (signatures, attachments)
└── docs/             # Documentation
```

## Next Steps

Phase 2: User authentication (registration, email verification, login) - IN PROGRESS

Remaining phases:
- Phase 3: Voucher models and CRUD
- Phase 4: Workflow engine and state machine
- Phase 5: Approval forms and views
- Phase 6: Dashboard and filters
- Phase 7: PDF generation
- Phase 8: Security hardening

## Support

For issues or questions, refer to the TRD document in the `docs/` folder.
