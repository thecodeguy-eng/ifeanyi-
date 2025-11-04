from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q
from decimal import Decimal
import json
import requests
from datetime import datetime

from .models import (
    User, WalletAddress, TradingBotPlan, UserBotSubscription,
    CopyTrader, CopyTradingSubscription, Transaction, Portfolio,
    Trade, PlatformSettings
)

# Crypto price API helper
def get_crypto_price(symbol):
    """Get real-time crypto price from CoinGecko API"""
    try:
        symbol_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'USDT': 'tether',
            'BNB': 'binancecoin',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
        }
        
        coin_id = symbol_map.get(symbol.upper(), symbol.lower())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        data = response.json()
        return Decimal(str(data[coin_id]['usd']))
    except:
        # Fallback prices if API fails
        fallback_prices = {
            'BTC': Decimal('45000'),
            'ETH': Decimal('2500'),
            'SOL': Decimal('100'),
            'USDT': Decimal('1'),
            'BNB': Decimal('300'),
            'XRP': Decimal('0.5'),
            'ADA': Decimal('0.4'),
            'DOGE': Decimal('0.08'),
        }
        return fallback_prices.get(symbol.upper(), Decimal('1'))


# Home page
def home(request):
    """Landing page"""
    return render(request, 'home.html')


# Authentication views
def register(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        legal_first_name = request.POST.get('legal_first_name')
        legal_last_name = request.POST.get('legal_last_name')
        phone_number = request.POST.get('phone_number')
        preferred_currency = request.POST.get('preferred_currency', 'USD')
        
        # Validation
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('register')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            legal_first_name=legal_first_name,
            legal_last_name=legal_last_name,
            phone_number=phone_number,
            preferred_currency=preferred_currency
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'register.html')


def user_login(request):
    """User login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Find user by email
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid credentials')
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    
    return render(request, 'login.html')


@login_required
def user_logout(request):
    """User logout"""
    logout(request)
    return redirect('home')


# Dashboard
@login_required
def dashboard(request):
    """Main dashboard"""
    user = request.user
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=user)[:10]
    
    # Get active bot subscriptions
    active_bots = UserBotSubscription.objects.filter(user=user, is_active=True)
    
    # Get active copy trading subscriptions
    active_copy_trades = CopyTradingSubscription.objects.filter(user=user, is_active=True)
    
    context = {
        'user': user,
        'recent_transactions': recent_transactions,
        'active_bots': active_bots,
        'active_copy_trades': active_copy_trades,
        'withdrawal_enabled': user.withdrawal_approved,
    }
    
    return render(request, 'dashboard.html', context)


# Portfolio
@login_required
def portfolio(request):
    """User portfolio"""
    user = request.user
    portfolio_items = Portfolio.objects.filter(user=user)
    
    # Update current values
    for item in portfolio_items:
        current_price = get_crypto_price(item.cryptocurrency)
        item.current_value = item.amount * current_price
        item.profit_loss = item.current_value - (item.amount * item.average_buy_price)
        item.save()
    
    context = {
        'portfolio_items': portfolio_items,
        'total_value': sum(item.current_value for item in portfolio_items),
    }
    
    return render(request, 'portfolio.html', context)


# Trading
@login_required
def trading(request):
    """Trading page"""
    if request.method == 'POST':
        trade_type = request.POST.get('trade_type')
        from_currency = request.POST.get('from_currency')
        to_currency = request.POST.get('to_currency')
        from_amount = Decimal(request.POST.get('from_amount'))
        
        # Get exchange rates
        if from_currency == 'USD':
            to_price = get_crypto_price(to_currency)
            to_amount = from_amount / to_price
            exchange_rate = to_price
        elif to_currency == 'USD':
            from_price = get_crypto_price(from_currency)
            to_amount = from_amount * from_price
            exchange_rate = from_price
        else:
            from_price = get_crypto_price(from_currency)
            to_price = get_crypto_price(to_currency)
            usd_value = from_amount * from_price
            to_amount = usd_value / to_price
            exchange_rate = from_price / to_price
        
        # Calculate fee
        settings = PlatformSettings.objects.first()
        fee_percentage = settings.trading_fee_percentage if settings else Decimal('0.5')
        fee = (from_amount * fee_percentage) / 100
        
        # Check balance
        if from_currency == 'USD':
            if request.user.account_balance < (from_amount + fee):
                messages.error(request, 'Insufficient balance')
                return redirect('trading')
        else:
            portfolio_item = Portfolio.objects.filter(
                user=request.user, cryptocurrency=from_currency
            ).first()
            if not portfolio_item or portfolio_item.amount < from_amount:
                messages.error(request, 'Insufficient cryptocurrency balance')
                return redirect('trading')
        
        # Execute trade
        trade = Trade.objects.create(
            user=request.user,
            trade_type=trade_type.upper(),
            from_currency=from_currency,
            to_currency=to_currency,
            from_amount=from_amount,
            to_amount=to_amount,
            exchange_rate=exchange_rate,
            fee=fee,
            status='COMPLETED'
        )
        
        # Update balances
        if from_currency == 'USD':
            request.user.account_balance -= (from_amount + fee)
            request.user.save()
        else:
            portfolio_item.amount -= from_amount
            portfolio_item.save()
        
        if to_currency == 'USD':
            request.user.account_balance += to_amount
            request.user.save()
        else:
            portfolio_item, created = Portfolio.objects.get_or_create(
                user=request.user,
                cryptocurrency=to_currency,
                defaults={
                    'amount': to_amount,
                    'average_buy_price': get_crypto_price(to_currency),
                    'current_value': to_amount * get_crypto_price(to_currency)
                }
            )
            if not created:
                portfolio_item.amount += to_amount
                portfolio_item.save()
        
        request.user.trading_count += 1
        request.user.save()
        
        messages.success(request, 'Trade executed successfully!')
        return redirect('portfolio')
    
    # Get available currencies
    portfolio_items = Portfolio.objects.filter(user=request.user)
    
    context = {
        'portfolio_items': portfolio_items,
    }
    
    return render(request, 'trading.html', context)


# Trading Bot Plans
@login_required
def trading_bot(request):
    """Trading bot plans"""
    plans = TradingBotPlan.objects.filter(is_active=True)
    user_subscriptions = UserBotSubscription.objects.filter(user=request.user, is_active=True)
    
    context = {
        'plans': plans,
        'user_subscriptions': user_subscriptions,
    }
    
    return render(request, 'trading_bot.html', context)


@login_required
def purchase_bot(request, plan_id):
    """Purchase trading bot plan"""
    plan = get_object_or_404(TradingBotPlan, id=plan_id, is_active=True)
    
    if request.method == 'POST':
        # Will redirect to payment page
        request.session['purchase_type'] = 'bot'
        request.session['purchase_id'] = plan_id
        request.session['purchase_amount'] = str(plan.price)
        return redirect('payment_page')
    
    return render(request, 'purchase_bot.html', {'plan': plan})


# Copy Trading
@login_required
def copy_trading(request):
    """Copy trading page"""
    traders = CopyTrader.objects.filter(is_active=True)
    
    context = {
        'traders': traders,
    }
    
    return render(request, 'copy_trading.html', context)


@login_required
def copy_trader_detail(request, trader_id):
    """Copy trader detail and subscription"""
    trader = get_object_or_404(CopyTrader, id=trader_id, is_active=True)
    
    if request.method == 'POST':
        # Calculate commission and proceed to payment
        commission = (trader.commission_percentage * trader.profit_percentage_per_day) / 100
        
        request.session['purchase_type'] = 'copy_trade'
        request.session['purchase_id'] = trader_id
        request.session['commission_amount'] = str(commission)
        return redirect('payment_page')
    
    context = {
        'trader': trader,
    }
    
    return render(request, 'copy_trader_detail.html', context)


# Deposit
@login_required
def deposit(request):
    """Deposit initiation"""
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        
        settings = PlatformSettings.objects.first()
        min_deposit = settings.minimum_deposit if settings else Decimal('50')
        
        if amount < min_deposit:
            messages.error(request, f'Minimum deposit is ${min_deposit}')
            return redirect('deposit')
        
        request.session['deposit_amount'] = str(amount)
        return redirect('payment_page')
    
    return render(request, 'deposit.html')


# Payment Page
@login_required
def payment_page(request):
    """Universal payment page for all transactions"""
    wallet_addresses = WalletAddress.objects.filter(is_active=True)
    
    # Get amount from session
    amount = None
    purchase_type = request.session.get('purchase_type', 'deposit')
    
    if 'deposit_amount' in request.session:
        amount = Decimal(request.session['deposit_amount'])
    elif 'purchase_amount' in request.session:
        amount = Decimal(request.session['purchase_amount'])
    
    # Calculate crypto amounts for each wallet
    crypto_amounts = {}
    for wallet in wallet_addresses:
        price = get_crypto_price(wallet.cryptocurrency)
        crypto_amounts[wallet.cryptocurrency] = amount / price if amount else 0
    
    if request.method == 'POST':
        selected_crypto = request.POST.get('cryptocurrency')
        proof_image = request.FILES.get('proof_image')
        blockchain_tx_id = request.POST.get('transaction_id')
        
        # Create transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='DEPOSIT' if purchase_type == 'deposit' else 'BOT_PURCHASE' if purchase_type == 'bot' else 'COPY_TRADE',
            amount=amount,
            currency=request.user.preferred_currency,
            crypto_currency=selected_crypto,
            crypto_amount=crypto_amounts[selected_crypto],
            proof_image=proof_image,
            blockchain_transaction_id=blockchain_tx_id,
            status='PENDING'
        )
        
        # Clear session
        request.session.pop('deposit_amount', None)
        request.session.pop('purchase_amount', None)
        request.session.pop('purchase_type', None)
        request.session.pop('purchase_id', None)
        
        messages.success(request, 'Payment proof submitted! Awaiting admin approval.')
        return redirect('dashboard')
    
    context = {
        'wallet_addresses': wallet_addresses,
        'amount': amount,
        'crypto_amounts': crypto_amounts,
        'purchase_type': purchase_type,
    }
    
    return render(request, 'payment_page.html', context)


# Withdrawal
@login_required
def withdrawal(request):
    """Withdrawal request"""
    if not request.user.withdrawal_approved:
        messages.error(request, 'Withdrawal not approved by admin yet')
        return redirect('dashboard')
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        crypto_currency = request.POST.get('cryptocurrency')
        wallet_address = request.POST.get('wallet_address')
        
        settings = PlatformSettings.objects.first()
        min_withdrawal = settings.minimum_withdrawal if settings else Decimal('50')
        
        if amount < min_withdrawal:
            messages.error(request, f'Minimum withdrawal is ${min_withdrawal}')
            return redirect('withdrawal')
        
        if request.user.account_balance < amount:
            messages.error(request, 'Insufficient balance')
            return redirect('withdrawal')
        
        # Calculate crypto amount
        crypto_price = get_crypto_price(crypto_currency)
        crypto_amount = amount / crypto_price
        
        # Create withdrawal transaction
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='WITHDRAWAL',
            amount=amount,
            currency=request.user.preferred_currency,
            crypto_currency=crypto_currency,
            crypto_amount=crypto_amount,
            description=f"Withdrawal to {wallet_address}",
            status='PENDING'
        )
        
        messages.success(request, 'Withdrawal request submitted! Awaiting admin approval.')
        return redirect('dashboard')
    
    return render(request, 'withdrawal.html')


# Transactions
@login_required
def transactions(request):
    """Transaction history"""
    all_transactions = Transaction.objects.filter(user=request.user)
    
    context = {
        'transactions': all_transactions,
    }
    
    return render(request, 'transactions.html', context)


# API endpoint for live crypto prices
@login_required
def get_crypto_prices(request):
    """API endpoint for real-time crypto prices"""
    symbols = ['BTC', 'ETH', 'SOL', 'USDT', 'BNB', 'XRP', 'ADA', 'DOGE']
    prices = {}
    
    for symbol in symbols:
        prices[symbol] = float(get_crypto_price(symbol))
    
    return JsonResponse(prices)