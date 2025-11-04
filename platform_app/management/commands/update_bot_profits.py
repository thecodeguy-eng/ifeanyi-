# File: management/commands/update_bot_profits.py
"""
Management command to update trading bot profits
Run with: python manage.py update_bot_profits
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from platform_app.models import UserBotSubscription, User, Transaction

class Command(BaseCommand):
    help = 'Update trading bot profits for active subscriptions'

    def handle(self, *args, **kwargs):
        active_subscriptions = UserBotSubscription.objects.filter(is_active=True)
        
        for subscription in active_subscriptions:
            # Calculate daily profit
            plan = subscription.plan
            investment = plan.price
            daily_profit = (investment * plan.daily_profit_percentage) / 100
            
            # Update user account
            user = subscription.user
            user.account_balance += daily_profit
            user.total_profit += daily_profit
            user.save()
            
            # Update subscription total
            subscription.total_earned += daily_profit
            subscription.save()
            
            # Create profit transaction
            Transaction.objects.create(
                user=user,
                transaction_type='PROFIT',
                amount=daily_profit,
                currency=user.preferred_currency,
                status='COMPLETED',
                description=f'Daily profit from {plan.plan_type} trading bot'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated profit for {user.username}: ${daily_profit}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {active_subscriptions.count()} bot subscriptions'
            )
        )
