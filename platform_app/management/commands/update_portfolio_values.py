# File: management/commands/update_portfolio_values.py
"""
Management command to update portfolio values
Run with: python manage.py update_portfolio_values
"""

from django.core.management.base import BaseCommand
from platform_app.models import Portfolio
from platform_app.views import get_crypto_price

class Command(BaseCommand):
    help = 'Update portfolio cryptocurrency values'

    def handle(self, *args, **kwargs):
        portfolios = Portfolio.objects.all()
        
        for portfolio in portfolios:
            try:
                current_price = get_crypto_price(portfolio.cryptocurrency)
                portfolio.current_value = portfolio.amount * current_price
                portfolio.profit_loss = portfolio.current_value - (
                    portfolio.amount * portfolio.average_buy_price
                )
                portfolio.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated {portfolio.user.username} - {portfolio.cryptocurrency}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error updating {portfolio.cryptocurrency}: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {portfolios.count()} portfolio items'
            )
        )

