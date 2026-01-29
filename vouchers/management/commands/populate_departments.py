from django.core.management.base import BaseCommand
from vouchers.models import Department


class Command(BaseCommand):
    help = 'Populate initial departments for the Payment Voucher System'

    def handle(self, *args, **kwargs):
        departments = [
            {'name': 'Finance', 'code': 'FIN'},
            {'name': 'Operations', 'code': 'OPS'},
            {'name': 'Marketing', 'code': 'MKT'},
            {'name': 'Human Resources', 'code': 'HR'},
            {'name': 'Information Technology', 'code': 'IT'},
            {'name': 'Maintenance', 'code': 'MNT'},
            {'name': 'Administration', 'code': 'ADM'},
            {'name': 'Customer Service', 'code': 'CS'},
        ]

        created_count = 0
        existing_count = 0

        for dept_data in departments:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={'name': dept_data['name']}
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"[+] Created department: {dept.name} ({dept.code})")
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(f"[-] Department already exists: {dept.name} ({dept.code})")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {created_count} created, {existing_count} already existed"
            )
        )
