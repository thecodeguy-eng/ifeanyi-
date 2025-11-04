# File: management/commands/update_copy_trade_profits.py
"""
Management command to update copy trading profits
Run with: python manage.py update_copy_trade_profits
"""

from django.core.management.base import BaseCommand
from platform_app.models import CopyTradingSubscription, Transaction

class Command(BaseCommand):
    help = 'Update copy trading profits for active subscriptions'

    def handle(self, *args, **kwargs):
        active_subscriptions = CopyTradingSubscription.objects.filter(is_active=True)
        
        for subscription in active_subscriptions:
            # Calculate daily profit
            trader = subscription.trader
            investment = subscription.amount_invested
            daily_profit = (investment * trader.profit_percentage_per_day) / 100
            
            # Deduct commission
            commission = (daily_profit * trader.commission_percentage) / 100
            net_profit = daily_profit - commission
            
            # Update user account
            user = subscription.user
            user.account_balance += net_profit
            user.total_profit += net_profit
            user.commission += commission
            user.save()
            
            # Update subscription total
            subscription.total_earned += net_profit
            subscription.save()
            
            # Create profit transaction
            Transaction.objects.create(
                user=user,
                transaction_type='PROFIT',
                amount=net_profit,
                currency=user.preferred_currency,
                status='COMPLETED',
                description=f'Copy trading profit from {trader.name}'
            )
            
            # Create commission transaction
            Transaction.objects.create(
                user=user,
                transaction_type='COMMISSION',
                amount=commission,
                currency=user.preferred_currency,
                status='COMPLETED',
                description=f'Commission for copy trading {trader.name}'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated copy trade for {user.username}: ${net_profit} profit, ${commission} commission'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {active_subscriptions.count()} copy trading subscriptions'
            )
        )

