# Khmer Font Setup for PDF Generation

## Current Setup
The voucher PDF template uses the Battambang font for Khmer language support.

## If Web Fonts Don't Work with WeasyPrint

WeasyPrint may not support loading fonts from external URLs. If you see missing characters or wrong fonts in the PDF, follow these steps:

### Step 1: Download Battambang Font
1. Visit: https://fonts.google.com/specimen/Battambang
2. Click "Download family" button
3. Extract the downloaded ZIP file

### Step 2: Create Fonts Directory
```bash
mkdir -p static/fonts
```

### Step 3: Copy Font Files
Copy these files from the extracted folder to `static/fonts/`:
- `Battambang-Regular.ttf`
- `Battambang-Bold.ttf`

### Step 4: Update voucher_pdf.html

Replace the @font-face declarations in `templates/vouchers/voucher_pdf.html`:

```css
/* Replace the existing @font-face declarations with: */

@font-face {
    font-family: 'Battambang';
    font-style: normal;
    font-weight: 400;
    src: url('file:///{{ STATIC_ROOT }}/fonts/Battambang-Regular.ttf') format('truetype');
}

@font-face {
    font-family: 'Battambang';
    font-style: normal;
    font-weight: 700;
    src: url('file:///{{ STATIC_ROOT }}/fonts/Battambang-Bold.ttf') format('truetype');
}
```

### Step 5: Update pdf_generator.py (if needed)

If the above doesn't work, you may need to pass the static directory path to WeasyPrint. Update `vouchers/pdf_generator.py`:

```python
# In the generate_pdf method, after setting base_url for media:

static_root = os.path.abspath(settings.STATIC_ROOT)
static_root = static_root.replace('\\', '/')
if not static_root.endswith('/'):
    static_root += '/'
```

### Alternative: System Fonts (Linux/Production)

If you're on Linux/Ubuntu server, you can install Khmer fonts system-wide:

```bash
sudo apt-get update
sudo apt-get install fonts-khmeros
```

Then update the font-family in voucher_pdf.html:
```css
body {
    font-family: 'Khmer OS Battambang', 'Battambang', 'Khmer OS', sans-serif;
    /* ... */
}
```

## Testing

After making changes, test the PDF generation:

```bash
python manage.py shell
```

```python
from vouchers.models import PaymentVoucher
from vouchers.pdf_generator import VoucherPDFGenerator

voucher = PaymentVoucher.objects.first()
pdf = VoucherPDFGenerator.generate_pdf(voucher)
```

Check if Khmer text displays correctly in the generated PDF.