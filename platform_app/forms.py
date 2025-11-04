from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import MinValueValidator
from decimal import Decimal
from .models import User, Transaction, Trade

class UserRegistrationForm(UserCreationForm):
    """User registration form"""
    legal_first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Legal First Name'
        })
    )
    legal_last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Legal Last Name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    preferred_currency = forms.ChoiceField(
        choices=User.CURRENCY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'legal_first_name', 'legal_last_name', 
                  'phone_number', 'preferred_currency', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password (min 8 characters)'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })


class UserLoginForm(forms.Form):
    """User login form"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (at least 8 characters)'
        })
    )


class DepositForm(forms.Form):
    """Deposit form"""
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('10'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to deposit',
            'min': '10',
            'step': '0.01'
        })
    )


class WithdrawalForm(forms.Form):
    """Withdrawal form"""
    CRYPTO_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('SOL', 'Solana'),
        ('USDT', 'Tether (USDT)'),
        ('BNB', 'Binance Coin'),
        ('XRP', 'Ripple'),
        ('ADA', 'Cardano'),
        ('DOGE', 'Dogecoin'),
    ]
    
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('10'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount to withdraw',
            'min': '10',
            'step': '0.01'
        })
    )
    cryptocurrency = forms.ChoiceField(
        choices=CRYPTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    wallet_address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your wallet address'
        })
    )


class PaymentProofForm(forms.Form):
    """Payment proof submission form"""
    CRYPTO_CHOICES = [
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('SOL', 'Solana'),
        ('USDT', 'Tether (USDT)'),
        ('BNB', 'Binance Coin'),
        ('XRP', 'Ripple'),
        ('ADA', 'Cardano'),
        ('DOGE', 'Dogecoin'),
    ]
    
    cryptocurrency = forms.ChoiceField(
        choices=CRYPTO_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    proof_image = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    transaction_id = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Blockchain Transaction ID (Optional)'
        })
    )


class TradeForm(forms.Form):
    """Trading form"""
    TRADE_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('SWAP', 'Swap'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('BTC', 'Bitcoin'),
        ('ETH', 'Ethereum'),
        ('SOL', 'Solana'),
        ('USDT', 'Tether'),
        ('BNB', 'Binance Coin'),
        ('XRP', 'Ripple'),
        ('ADA', 'Cardano'),
        ('DOGE', 'Dogecoin'),
    ]
    
    trade_type = forms.ChoiceField(
        choices=TRADE_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    from_currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    to_currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    from_amount = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount',
            'step': '0.00000001'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        from_currency = cleaned_data.get('from_currency')
        to_currency = cleaned_data.get('to_currency')
        
        if from_currency == to_currency:
            raise forms.ValidationError("Cannot trade same currency")
        
        return cleaned_data


class CopyTradeForm(forms.Form):
    """Copy trading subscription form"""
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('100'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Investment Amount (minimum $100)',
            'min': '100',
            'step': '0.01'
        })
    )
    duration_days = forms.IntegerField(
        validators=[MinValueValidator(7)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Duration in days (minimum 7)',
            'min': '7'
        })
    )