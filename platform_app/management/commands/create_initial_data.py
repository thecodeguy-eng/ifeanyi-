

# File: management/commands/create_initial_data.py
"""
Management command to create initial data
Run with: python manage.py create_initial_data
"""

from django.core.management.base import BaseCommand
from platform_app.models import (
    WalletAddress, TradingBotPlan, CopyTrader, PlatformSettings
)
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create initial data for the platform'

    def handle(self, *args, **kwargs):
        # Create wallet addresses
        wallets = [
            {'cryptocurrency': 'BTC', 'wallet_address': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'},
            {'cryptocurrency': 'ETH', 'wallet_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'},
            {'cryptocurrency': 'SOL', 'wallet_address': 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK'},
            {'cryptocurrency': 'USDT', 'wallet_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'},
            {'cryptocurrency': 'BNB', 'wallet_address': 'bnb1grpf0955h0ykzq3ar5nmum7y6gdfl6lxfn46h2'},
        ]
        
        for wallet in wallets:
            WalletAddress.objects.get_or_create(**wallet)
        
        self.stdout.write(self.style.SUCCESS('Created wallet addresses'))
        
        # Create trading bot plans
        plans = [
            {
                'plan_type': 'BASIC',
                'price': Decimal('1000'),
                'daily_profit_percentage': Decimal('2.5'),
                'features': ['24/7 Trading', 'Basic Analytics', 'Email Support']
            },
            {
                'plan_type': 'INTERMEDIATE',
                'price': Decimal('5000'),
                'daily_profit_percentage': Decimal('3.5'),
                'features': ['24/7 Trading', 'Advanced Analytics', 'Priority Support', 'Risk Management']
            },
            {
                'plan_type': 'ADVANCED',
                'price': Decimal('7000'),
                'daily_profit_percentage': Decimal('4.5'),
                'features': ['24/7 Trading', 'AI Analytics', 'VIP Support', 'Advanced Risk Management', 'Custom Strategies']
            },
            {
                'plan_type': 'PRO',
                'price': Decimal('10000'),
                'daily_profit_percentage': Decimal('5.5'),
                'features': ['24/7 Trading', 'Premium AI Analytics', 'Dedicated Account Manager', 'Maximum Risk Protection', 'Exclusive Strategies', 'API Access']
            },
        ]
        
        for plan in plans:
            TradingBotPlan.objects.get_or_create(
                plan_type=plan['plan_type'],
                defaults=plan
            )
        
        self.stdout.write(self.style.SUCCESS('Created trading bot plans'))
        
        # Create sample copy traders
        traders = [
            {
                'name': 'John Smith',
                'country': 'United States',
                'country_flag': 'US',
                'rating': Decimal('4.8'),
                'profit_percentage_per_day': Decimal('3.2'),
                'total_trades': 1250,
                'followers_count': 850,
                'roi': Decimal('245.5'),
                'commission_percentage': Decimal('10'),
            },
            {
                'name': 'Emma Chen',
                'country': 'Singapore',
                'country_flag': 'SG',
                'rating': Decimal('4.9'),
                'profit_percentage_per_day': Decimal('4.5'),
                'total_trades': 2100,
                'followers_count': 1200,
                'roi': Decimal('320.8'),
                'commission_percentage': Decimal('15'),
            },
            {
                'name': 'Michael Brown',
                'country': 'United Kingdom',
                'country_flag': 'GB',
                'rating': Decimal('4.7'),
                'profit_percentage_per_day': Decimal('2.8'),
                'total_trades': 980,
                'followers_count': 650,
                'roi': Decimal('198.3'),
                'commission_percentage': Decimal('8'),
            },
        ]
        
        for trader in traders:
            CopyTrader.objects.get_or_create(
                name=trader['name'],
                defaults=trader
            )
        
        self.stdout.write(self.style.SUCCESS('Created copy traders'))
        
        # Create platform settings
        settings, created = PlatformSettings.objects.get_or_create(
            id=1,
            defaults={
                'minimum_deposit': Decimal('50'),
                'minimum_withdrawal': Decimal('50'),
                'trading_fee_percentage': Decimal('0.5'),
                'withdrawal_fee_percentage': Decimal('1'),
                'referral_bonus_percentage': Decimal('5'),
            }
        )
        
        self.stdout.write(self.style.SUCCESS('Created platform settings'))
        self.stdout.write(self.style.SUCCESS('Initial data creation completed!'))