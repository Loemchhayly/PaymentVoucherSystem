from django.core.management.base import BaseCommand
from vouchers.models import CompanyBankAccount


class Command(BaseCommand):
    help = 'Add sample company bank accounts'

    def handle(self, *args, **options):
        # Create sample accounts
        accounts = [
            {
                'company_name': 'Phat Phnom Penh Co.,Ltd',
                'account_number': '002 232 482',
                'currency': 'USD',
                'bank': 'ABA Bank',
            },
            {
                'company_name': 'Phat Phnom Penh Co.,Ltd',
                'account_number': '3484-02-999990-6-6',
                'currency': 'USD',
                'bank': 'ACLEDA Bank',
            },
            {
                'company_name': 'Phat Phnom Penh Co.,Ltd',
                'account_number': '002 232 485',
                'currency': 'KHR',
                'bank': 'ABA Bank',
            },
        ]

        created_count = 0
        for account_data in accounts:
            account, created = CompanyBankAccount.objects.get_or_create(
                account_number=account_data['account_number'],
                bank=account_data['bank'],
                defaults=account_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created: {account.get_display_name()}'
                    )
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Already exists: {account.get_display_name()}'
                    )
                )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully created {created_count} company bank account(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\nNo new accounts created. All accounts already exist.'
                )
            )
