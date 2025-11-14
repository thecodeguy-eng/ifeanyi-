from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

from cloudinary.models import CloudinaryField

class User(AbstractUser):
    """Extended User model with additional fields"""
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
    ]
    
    legal_first_name = models.CharField(max_length=100)
    legal_last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    preferred_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    account_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    trading_count = models.IntegerField(default=0)
    total_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_withdrawal = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    withdrawal_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.legal_first_name} {self.legal_last_name}"


class WalletAddress(models.Model):
    """Company wallet addresses for different cryptocurrencies"""
    CRYPTO_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('SOL', 'Solana'),
        ('USDT', 'Tether (Trc)'),
        ('BNB', 'Binance Coin'),
        ('XRP', 'Ripple'),
        ('ADA', 'Cardano'),
        ('DOGE', 'Dogecoin'),
    ]
    
    cryptocurrency = models.CharField(max_length=10, choices=CRYPTO_CHOICES, unique=True)
    wallet_address = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'wallet_addresses'
        verbose_name_plural = 'Wallet Addresses'
    
    def __str__(self):
        return f"{self.cryptocurrency} - {self.wallet_address}"


class TradingBotPlan(models.Model):
    """Trading bot subscription plans"""
    PLAN_CHOICES = [
        ('BASIC', 'Basic'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('PRO', 'Pro'),
    ]
    
    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(0)])
    daily_profit_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_bot_plans'
    
    def __str__(self):
        return f"{self.plan_type} - ${self.price}"


class UserBotSubscription(models.Model):
    """User's trading bot subscriptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bot_subscriptions')
    plan = models.ForeignKey(TradingBotPlan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    total_earned = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'user_bot_subscriptions'
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.plan_type}"


class CopyTrader(models.Model):
    """Professional traders available for copy trading"""
    name = models.CharField(max_length=100)
    profile_image = CloudinaryField('trader_profiles', null=True, blank=True)
    country = models.CharField(max_length=100)
    country_flag = models.CharField(max_length=10)  # Country code for flag
    rating = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0)])
    profit_percentage_per_day = models.DecimalField(max_digits=5, decimal_places=2)
    total_trades = models.IntegerField(default=0)
    followers_count = models.IntegerField(default=0)
    roi = models.DecimalField(max_digits=5, decimal_places=2)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'copy_traders'
    
    def __str__(self):
        return self.name


class CopyTradingSubscription(models.Model):
    """User's copy trading subscriptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='copy_trading_subs')
    trader = models.ForeignKey(CopyTrader, on_delete=models.CASCADE)
    amount_invested = models.DecimalField(max_digits=20, decimal_places=2)
    commission_paid = models.DecimalField(max_digits=20, decimal_places=2)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    total_earned = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'copy_trading_subscriptions'
    
    def __str__(self):
        return f"{self.user.username} copying {self.trader.name}"


class Transaction(models.Model):
    """All user transactions"""
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('BOT_PURCHASE', 'Trading Bot Purchase'),
        ('COPY_TRADE', 'Copy Trading'),
        ('TRADE', 'Trade'),
        ('SWAP', 'Currency Swap'),
        ('PROFIT', 'Profit'),
        ('COMMISSION', 'Commission'),
        ('BONUS', 'Bonus'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    ]
    
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    proof_image = CloudinaryField('payment_proofs', null=True, blank=True)
    blockchain_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    crypto_currency = models.CharField(max_length=10, null=True, blank=True)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ${self.amount}"


class Portfolio(models.Model):
    """User's cryptocurrency portfolio"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio')
    cryptocurrency = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=20, decimal_places=8, validators=[MinValueValidator(0)])
    average_buy_price = models.DecimalField(max_digits=20, decimal_places=2)
    current_value = models.DecimalField(max_digits=20, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portfolio'
        unique_together = ['user', 'cryptocurrency']
    
    def __str__(self):
        return f"{self.user.username} - {self.cryptocurrency}: {self.amount}"


class Trade(models.Model):
    """Individual trades made by users"""
    TRADE_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('SWAP', 'Swap'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    from_currency = models.CharField(max_length=10)
    to_currency = models.CharField(max_length=10)
    from_amount = models.DecimalField(max_digits=20, decimal_places=8)
    to_amount = models.DecimalField(max_digits=20, decimal_places=8)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=8)
    fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='COMPLETED')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trades'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.trade_type} {self.from_currency} to {self.to_currency}"


class PlatformSettings(models.Model):
    """Global platform settings"""
    maintenance_mode = models.BooleanField(default=False)
    minimum_deposit = models.DecimalField(max_digits=20, decimal_places=2, default=50)
    minimum_withdrawal = models.DecimalField(max_digits=20, decimal_places=2, default=50)
    trading_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.5)
    withdrawal_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    referral_bonus_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'platform_settings'
        verbose_name_plural = 'Platform Settings'
    
    def __str__(self):
        return f"Platform Settings - Updated: {self.updated_at}"
    

# Add these models to your existing models.py file

class SupportChat(models.Model):
    """Support chat sessions"""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('CLOSED', 'Closed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_chats')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'support_chats'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Chat #{self.id} - {self.user.username} - {self.status}"


class SupportMessage(models.Model):
    """Individual messages in support chats"""
    SENDER_TYPES = [
        ('USER', 'User'),
        ('SUPPORT', 'Support'),
    ]
    
    chat = models.ForeignKey(SupportChat, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    sender_name = models.CharField(max_length=100)  # Username or Support Agent name
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'support_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender_name}: {self.message[:50]}"

class UserActivity(models.Model):
    """Track all user activities and page visits"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    page_url = models.CharField(max_length=500)
    page_title = models.CharField(max_length=200, null=True, blank=True)
    action_type = models.CharField(max_length=50, default='PAGE_VIEW')  # PAGE_VIEW, LOGIN, LOGOUT, DEPOSIT, etc.
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(null=True, blank=True)  # Time spent on page in seconds
    
    class Meta:
        db_table = 'user_activities'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f"{username} - {self.page_url} - {self.timestamp}"


class AdminUser(models.Model):
    """Custom admin users separate from regular users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    role = models.CharField(max_length=50, choices=[
        ('SUPER_ADMIN', 'Super Admin'),
        ('ADMIN', 'Admin'),
        ('MODERATOR', 'Moderator'),
    ], default='ADMIN')
    permissions = models.JSONField(default=dict)  # Custom permissions
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_users'
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"


class SystemLog(models.Model):
    """System-wide logs for admin monitoring"""
    LOG_LEVELS = [
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    level = models.CharField(max_length=20, choices=LOG_LEVELS, default='INFO')
    action = models.CharField(max_length=100)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.level} - {self.action} - {self.timestamp}"