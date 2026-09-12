from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Sum, Q
from django.urls import reverse
from django.templatetags.static import static
from decimal import Decimal
import json
import requests
from datetime import datetime, timedelta
import logging
from django.utils import timezone
from .email_service import send_password_reset_code, send_welcome_email, send_deposit_reminder, send_admin_new_registration_email
from .geoip import get_country_from_ip, get_client_ip

from .models import (
    User, WalletAddress, TradingBotPlan, UserBotSubscription,
    CopyTrader, CopyTradingSubscription, Transaction, Portfolio,
    Trade, PlatformSettings, SupportChat, SupportMessage, PasswordResetCode,
    InvestmentPlan, UserInvestment, UserActivity,
)

# Set up logging
logger = logging.getLogger(__name__)



def onboarding(request):
    """Onboarding page for new users"""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'onboarding.html')



def forgot_password(request):
    """Step 1: Request password reset - send code to email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()  # normalize email

        try:
            user = User.objects.get(email__iexact=email)
            canonical_email = user.email  # use the exact email stored in DB

            # Invalidate any existing unused codes for this user
            PasswordResetCode.objects.filter(
                user=user,
                is_used=False
            ).update(is_used=True)

            # Create new reset code
            reset_code = PasswordResetCode.objects.create(
                user=user,
                email=canonical_email  # always store the DB email, not user input
            )

            # Send email with reset code
            user_name = f"{user.legal_first_name} {user.legal_last_name}".strip() or user.username
            result = send_password_reset_code(canonical_email, user_name, reset_code.code)

            if result.get('success'):
                # Store the canonical DB email in session for next step
                request.session['reset_email'] = canonical_email
                messages.success(
                    request,
                    f'A 6-digit reset code has been sent to {canonical_email}. Please check your inbox.'
                )
                return redirect('verify_reset_code')
            else:
                logger.error(f"Failed to send reset email: {result.get('error')}")
                messages.error(
                    request,
                    'Failed to send reset code. Please try again later.'
                )

        except User.DoesNotExist:
            # Don't reveal that email doesn't exist (security best practice)
            messages.info(
                request,
                'If an account exists with that email, a reset code has been sent.'
            )
            # Still redirect to give impression code was sent
            request.session['reset_email'] = email
            return redirect('verify_reset_code')

    return render(request, 'forgot_password.html')


def verify_reset_code(request):
    """Step 2: Verify the reset code sent to email"""
    # Check if email is in session
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please start the password reset process again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()  # strip any accidental whitespace

        try:
            # Find the reset code
            reset_code = PasswordResetCode.objects.filter(
                email=email,
                code=code,
                is_used=False
            ).latest('created_at')
            
            # Check if code is valid
            if reset_code.is_valid():
                # Store code in session for next step
                request.session['reset_code_id'] = reset_code.id
                messages.success(request, 'Code verified! Please enter your new password.')
                return redirect('reset_password')
            else:
                messages.error(request, 'This code has expired. Please request a new one.')
                return redirect('forgot_password')
                
        except PasswordResetCode.DoesNotExist:
            messages.error(request, 'Invalid reset code. Please try again.')
    
    context = {
        'email': email,
        'masked_email': mask_email(email)
    }
    return render(request, 'verify_reset_code.html', context)


def reset_password(request):
    """Step 3: Set new password"""
    # Check if code_id is in session
    code_id = request.session.get('reset_code_id')
    if not code_id:
        messages.error(request, 'Please complete the verification step first.')
        return redirect('forgot_password')
    
    try:
        reset_code = PasswordResetCode.objects.get(id=code_id, is_used=False)
        
        # Double-check code is still valid
        if not reset_code.is_valid():
            messages.error(request, 'Reset code has expired. Please start again.')
            # Clean up session
            request.session.pop('reset_email', None)
            request.session.pop('reset_code_id', None)
            return redirect('forgot_password')
        
    except PasswordResetCode.DoesNotExist:
        messages.error(request, 'Invalid reset session. Please start again.')
        return redirect('forgot_password')
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validate passwords match
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'reset_password.html')
        
        # Validate password length
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'reset_password.html')
        
        # Update user password
        user = reset_code.user
        user.set_password(password1)
        user.save()
        
        # Mark code as used
        reset_code.is_used = True
        reset_code.save()
        
        # Clean up session
        request.session.pop('reset_email', None)
        request.session.pop('reset_code_id', None)
        
        # Log the password reset
        logger.info(f"Password reset successful for user: {user.username}")
        
        messages.success(
            request, 
            'Password reset successful! You can now login with your new password.'
        )
        return redirect('login')
    
    return render(request, 'reset_password.html', {'email': reset_code.email})


def resend_reset_code(request):
    """Resend reset code to email"""
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
    
    try:
        user = User.objects.get(email=email)
        
        # Invalidate old codes
        PasswordResetCode.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)
        
        # Create new code
        reset_code = PasswordResetCode.objects.create(
            user=user,
            email=email
        )
        
        # Send email
        user_name = f"{user.legal_first_name} {user.legal_last_name}"
        result = send_password_reset_code(email, user_name, reset_code.code)
        
        if result.get('success'):
            messages.success(request, 'A new reset code has been sent to your email.')
        else:
            messages.error(request, 'Failed to send reset code. Please try again.')
            
    except User.DoesNotExist:
        messages.info(request, 'If an account exists, a new code has been sent.')
    
    return redirect('verify_reset_code')


def mask_email(email):
    """Mask email for privacy: user@example.com -> u***@example.com"""
    try:
        username, domain = email.split('@')
        if len(username) <= 2:
            masked_username = username[0] + '***'
        else:
            masked_username = username[0] + '***' + username[-1]
        return f"{masked_username}@{domain}"
    except:
        return email

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)


def handler403(request, exception):
    """Custom 403 error handler"""
    return render(request, '403.html', status=403)


def handler500(request):
    """Custom 500 error handler"""
    return render(request, '500.html', status=500)


def get_crypto_price(symbol):
    """
    Get real-time crypto price from CoinGecko API with improved error handling
    Returns the price as a Decimal
    Uses November 2025 prices as fallback
    """
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
            'AVAX': 'avalanche-2',
            'LTC': 'litecoin',
            'MATIC': 'matic-network',
        }
        
        coin_id = symbol_map.get(symbol.upper())
        if not coin_id:
            logger.warning(f"Unknown cryptocurrency symbol: {symbol}")
            return Decimal('1')
        
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        logger.info(f"Fetching price for {symbol} from CoinGecko API")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if coin_id in data and 'usd' in data[coin_id]:
            price = Decimal(str(data[coin_id]['usd']))
            logger.info(f"Successfully fetched {symbol} price: ${price}")
            return price
        else:
            logger.error(f"Price data not found in API response for {symbol}")
            raise ValueError(f"Price not found for {symbol}")
            
    except requests.exceptions.Timeout:
        logger.error(f"API request timeout for {symbol}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error for {symbol}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting price for {symbol}: {e}")
    
    fallback_prices = {
        'BTC': Decimal('102000'),
        'ETH': Decimal('3350'),
        'SOL': Decimal('158'),
        'USDT': Decimal('1.00'),
        'BNB': Decimal('943'),
        'XRP': Decimal('2.23'),
        'ADA': Decimal('0.53'),
        'DOGE': Decimal('0.163'),
        'AVAX': Decimal('38'),
        'LTC': Decimal('105'),
        'MATIC': Decimal('0.55'),
    }
    
    fallback_price = fallback_prices.get(symbol.upper(), Decimal('1'))
    logger.warning(f"Using fallback price for {symbol}: ${fallback_price}")
    return fallback_price


# Home page
def home(request):
    """Landing page"""
    plans = InvestmentPlan.objects.filter(is_active=True).order_by('minimum_amount')[:4]
    return render(request, 'home.html', {'plans': plans})


# Authentication views

def register(request):
    """User registration with welcome email"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        legal_first_name = request.POST.get('legal_first_name')
        legal_last_name = request.POST.get('legal_last_name')
        preferred_currency = request.POST.get('preferred_currency', 'USD')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('register')
        
        # Resolve the registrant's country from their IP (best-effort, never blocks signup)
        ip_address = get_client_ip(request)
        country = get_country_from_ip(ip_address)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            legal_first_name=legal_first_name,
            legal_last_name=legal_last_name,
            preferred_currency=preferred_currency,
            country=country,
        )

        full_name = f"{legal_first_name} {legal_last_name}".strip() or username
        logo_url = request.build_absolute_uri(static('platform_app/img/logo-512.png'))

        # Log this as its own activity so it shows up in the admin Activity Center
        # (registration is a POST, which UserActivityMiddleware doesn't track)
        try:
            if not request.session.session_key:
                request.session.create()
            UserActivity.objects.create(
                user=user,
                session_id=request.session.session_key,
                ip_address=ip_address[:45] if ip_address else None,
                country=country,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                page_url='/register/',
                page_title='Registration',
                action_type='REGISTER',
            )
        except Exception as e:
            logger.error(f"Failed to log registration activity: {e}")

        # Send welcome email immediately
        try:
            dashboard_url = request.build_absolute_uri(reverse('dashboard'))
            send_welcome_email(user.email, full_name, dashboard_url=dashboard_url, logo_url=logo_url)
            logger.info(f"Welcome email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")

        # Schedule deposit reminder email
        try:
            deposit_url = request.build_absolute_uri(reverse('deposit'))
            send_deposit_reminder(user.email, full_name, deposit_url=deposit_url, logo_url=logo_url)
            logger.info(f"Deposit reminder email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send deposit reminder email: {e}")

        # Notify the admin inbox of the new registration
        try:
            admin_url = request.build_absolute_uri(reverse('admin_user_detail', args=[user.id]))
            send_admin_new_registration_email(
                username=user.username,
                email=user.email,
                account_id=user.id,
                country=country,
                registered_at=timezone.now().strftime('%B %d, %Y %H:%M UTC'),
                admin_url=admin_url,
                logo_url=logo_url,
            )
        except Exception as e:
            logger.error(f"Failed to send admin registration notification: {e}")

        # Auto-login the new user and redirect to onboarding
        login(request, user)
        messages.success(request, 'Account created successfully! Welcome to Mirrorwavetrades Global.')
        return redirect('onboarding')
    
    return render(request, 'register.html')

def user_login(request):
    """User login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
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
    recent_transactions = Transaction.objects.filter(user=user)[:10]
    active_bots = UserBotSubscription.objects.filter(user=user, is_active=True)
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
        
        settings = PlatformSettings.objects.first()
        fee_percentage = settings.trading_fee_percentage if settings else Decimal('0.5')
        fee = (from_amount * fee_percentage) / 100
        to_amount = to_amount * (1 - (fee_percentage / 100))
        
        if from_currency == 'USD':
            if request.user.account_balance < from_amount:
                messages.error(request, 'Insufficient balance')
                return redirect('trading')
        else:
            portfolio_item = Portfolio.objects.filter(
                user=request.user, cryptocurrency=from_currency
            ).first()
            if not portfolio_item or portfolio_item.amount < from_amount:
                messages.error(request, 'Insufficient cryptocurrency balance')
                return redirect('trading')
        
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
        
        if from_currency == 'USD':
            request.user.account_balance -= from_amount
            request.user.save()
        else:
            portfolio_item.amount -= from_amount
            if portfolio_item.amount <= 0:
                portfolio_item.delete()
            else:
                portfolio_item.save()
        
        if to_currency == 'USD':
            request.user.account_balance += to_amount
            request.user.save()
        else:
            current_price = get_crypto_price(to_currency)
            portfolio_item, created = Portfolio.objects.get_or_create(
                user=request.user,
                cryptocurrency=to_currency,
                defaults={
                    'amount': to_amount,
                    'average_buy_price': current_price,
                    'current_value': to_amount * current_price
                }
            )
            if not created:
                total_value = (portfolio_item.amount * portfolio_item.average_buy_price) + (to_amount * current_price)
                portfolio_item.amount += to_amount
                portfolio_item.average_buy_price = total_value / portfolio_item.amount
                portfolio_item.current_value = portfolio_item.amount * current_price
                portfolio_item.save()
        
        request.user.trading_count += 1
        request.user.save()
        
        messages.success(request, f'Trade executed successfully! Received {to_amount:.8f} {to_currency}')
        return redirect('portfolio')
    
    portfolio_items = Portfolio.objects.filter(user=request.user)
    context = {'portfolio_items': portfolio_items}
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
    context = {'traders': traders}
    return render(request, 'copy_trading.html', context)


@login_required
def copy_trader_detail(request, trader_id):
    """Copy trader detail and subscription"""
    trader = get_object_or_404(CopyTrader, id=trader_id, is_active=True)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        
        if amount < 100:
            return JsonResponse({'success': False, 'message': 'Minimum investment is $100'})
        
        # Check if user has sufficient balance
        if request.user.account_balance < amount:
            return JsonResponse({'success': False, 'message': 'Insufficient account balance. Please deposit funds first.'})
        
        # Deduct amount from user balance
        request.user.account_balance -= amount
        request.user.save()
        
        # Calculate commission
        commission = (amount * trader.commission_percentage) / 100
        
        # Create copy trading subscription
        subscription = CopyTradingSubscription.objects.create(
            user=request.user,
            trader=trader,
            amount_invested=amount,
            commission_paid=commission,
            is_active=True,
            total_earned=Decimal('0')
        )
        
        # Update trader followers count
        trader.followers_count += 1
        trader.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=request.user,
            transaction_type='COPY_TRADE',
            amount=amount,
            currency=request.user.preferred_currency,
            status='COMPLETED',
            description=f'Copy trading investment with {trader.name}'
        )
        
        messages.success(request, f'Successfully copying {trader.name}\'s trades!')
        return JsonResponse({'success': True, 'message': f'Successfully copying {trader.name}\'s trades! Investment: ${amount}'})
    
    context = {'trader': trader}
    return render(request, 'copy_trader_detail.html', context)


# ── Investment Plans ──────────────────────────────────────────────────────────

@login_required
def investment_plans(request):
    """List all available investment plans."""
    plans = InvestmentPlan.objects.filter(is_active=True).order_by('minimum_amount')
    user_active_investments = UserInvestment.objects.filter(
        user=request.user, status='ACTIVE'
    ).select_related('plan')

    context = {
        'plans': plans,
        'user_active_investments': user_active_investments,
        'withdrawal_enabled': request.user.withdrawal_approved,
        'active_page': 'investment_plans',
    }
    return render(request, 'investment_plans.html', context)


@login_required
def investment_plan_detail(request, plan_id):
    """Detail page for a single investment plan with enroll form."""
    plan = get_object_or_404(InvestmentPlan, id=plan_id, is_active=True)

    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except Exception:
            return JsonResponse({'success': False, 'message': 'Invalid amount.'})

        # Validate minimum
        if amount < plan.minimum_amount:
            return JsonResponse({
                'success': False,
                'message': f'Minimum investment for this plan is ${plan.minimum_amount:,.2f}.'
            })

        # Validate maximum
        if plan.maximum_amount and amount > plan.maximum_amount:
            return JsonResponse({
                'success': False,
                'message': f'Maximum investment for this plan is ${plan.maximum_amount:,.2f}.'
            })

        # Check balance
        if request.user.account_balance < amount:
            return JsonResponse({
                'success': False,
                'message': 'Insufficient account balance. Please deposit funds first.'
            })

        # Deduct balance
        request.user.account_balance -= amount
        request.user.save()

        # Calculate returns
        expected_return = (amount * plan.maturity_multiplier).quantize(Decimal('0.01'))
        profit_amount   = (expected_return - amount).quantize(Decimal('0.01'))
        end_date        = timezone.now() + timedelta(days=plan.duration_days)

        # Create investment record
        investment = UserInvestment.objects.create(
            user=request.user,
            plan=plan,
            amount_invested=amount,
            expected_return=expected_return,
            profit_amount=profit_amount,
            end_date=end_date,
            status='ACTIVE',
        )

        # Record transaction
        Transaction.objects.create(
            user=request.user,
            transaction_type='INVESTMENT',
            amount=amount,
            currency=request.user.preferred_currency,
            status='COMPLETED',
            description=f'Investment in {plan.name} plan (#{investment.id})',
        )

        logger.info(f"User {request.user.username} invested ${amount} in plan {plan.name}")

        return JsonResponse({
            'success': True,
            'message': (
                f'Successfully invested ${amount:,.2f} in the {plan.name} plan! '
                f'Expected return: ${expected_return:,.2f} in {plan.duration_days} days.'
            ),
            'redirect': '/investments/my/'
        })

    context = {
        'plan': plan,
        'user': request.user,
        'withdrawal_enabled': request.user.withdrawal_approved,
        'active_page': 'investment_plans',
    }
    return render(request, 'investment_detail.html', context)


@login_required
def my_investments(request):
    """User's investment portfolio."""
    investments = UserInvestment.objects.filter(
        user=request.user
    ).select_related('plan').order_by('-start_date')

    total_invested = sum(
        i.amount_invested for i in investments if i.status != 'CANCELLED'
    )
    total_earned = sum(
        i.profit_amount for i in investments if i.status == 'COMPLETED'
    )
    active_count = sum(1 for i in investments if i.status == 'ACTIVE')

    context = {
        'investments': investments,
        'total_invested': total_invested,
        'total_earned': total_earned,
        'active_count': active_count,
        'withdrawal_enabled': request.user.withdrawal_approved,
        'active_page': 'my_investments',
    }
    return render(request, 'my_investments.html', context)


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


# Payment Page with Real-time Crypto Conversion
@login_required
def payment_page(request):
    """Universal payment page with real-time crypto prices"""
    wallet_addresses = WalletAddress.objects.filter(is_active=True)
    
    amount = None
    purchase_type = request.session.get('purchase_type', 'deposit')
    
    if 'deposit_amount' in request.session:
        amount = Decimal(request.session['deposit_amount'])
    elif 'purchase_amount' in request.session:
        amount = Decimal(request.session['purchase_amount'])
    
    if amount is None:
        messages.error(request, 'Invalid payment session. Please try again.')
        return redirect('dashboard')
    
    crypto_amounts = {}
    for wallet in wallet_addresses:
        try:
            price = get_crypto_price(wallet.cryptocurrency)
            if price > 0:
                crypto_amounts[wallet.cryptocurrency] = amount / price
                logger.info(f"{wallet.cryptocurrency}: ${amount} = {crypto_amounts[wallet.cryptocurrency]:.8f} {wallet.cryptocurrency} @ ${price}")
            else:
                crypto_amounts[wallet.cryptocurrency] = Decimal('0')
                logger.warning(f"Invalid price for {wallet.cryptocurrency}")
        except Exception as e:
            logger.error(f"Error calculating crypto amount for {wallet.cryptocurrency}: {e}")
            crypto_amounts[wallet.cryptocurrency] = Decimal('0')
    
    if request.method == 'POST':
        selected_crypto = request.POST.get('cryptocurrency')
        proof_image = request.FILES.get('proof_image')
        blockchain_tx_id = request.POST.get('transaction_id', '')
        
        if not selected_crypto or selected_crypto not in crypto_amounts:
            messages.error(request, 'Please select a valid cryptocurrency')
            context = {
                'wallet_addresses': wallet_addresses,
                'amount': amount,
                'crypto_amounts': crypto_amounts,
                'purchase_type': purchase_type,
            }
            return render(request, 'payment_page.html', context)
        
        if not proof_image:
            messages.error(request, 'Please upload payment proof screenshot')
            context = {
                'wallet_addresses': wallet_addresses,
                'amount': amount,
                'crypto_amounts': crypto_amounts,
                'purchase_type': purchase_type,
            }
            return render(request, 'payment_page.html', context)
        
        crypto_price = get_crypto_price(selected_crypto)
        actual_crypto_amount = amount / crypto_price if crypto_price > 0 else Decimal('0')
        
        transaction = Transaction.objects.create(
            user=request.user,
            transaction_type='DEPOSIT' if purchase_type == 'deposit' else 'BOT_PURCHASE' if purchase_type == 'bot' else 'COPY_TRADE',
            amount=amount,
            currency=request.user.preferred_currency,
            crypto_currency=selected_crypto,
            crypto_amount=actual_crypto_amount,
            proof_image=proof_image,
            blockchain_transaction_id=blockchain_tx_id,
            status='PENDING'
        )
        
        logger.info(f"Payment proof submitted: User {request.user.username}, Amount ${amount}, Crypto {actual_crypto_amount:.8f} {selected_crypto}")
        
        request.session.pop('deposit_amount', None)
        request.session.pop('purchase_amount', None)
        request.session.pop('purchase_type', None)
        request.session.pop('purchase_id', None)
        
        messages.success(request, 'Payment proof submitted successfully! Your transaction is being verified.')
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
        
        crypto_price = get_crypto_price(crypto_currency)
        crypto_amount = amount / crypto_price if crypto_price > 0 else Decimal('0')
        
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
        
        logger.info(f"Withdrawal requested: User {request.user.username}, Amount ${amount}, Crypto {crypto_amount:.8f} {crypto_currency}")
        
        messages.success(request, 'Withdrawal request submitted! Awaiting admin approval.')
        return redirect('dashboard')
    
    return render(request, 'withdrawal.html')


# Transactions
@login_required
def transactions(request):
    """Transaction history"""
    all_transactions = Transaction.objects.filter(user=request.user)
    context = {'transactions': all_transactions}
    return render(request, 'transactions.html', context)


# API endpoint for live crypto prices
def get_crypto_prices(request):
    """API endpoint for real-time crypto prices.

    Fetches all symbols in a single CoinGecko request (instead of one request
    per symbol) and caches the result briefly, so this stays fast even when
    polled every few seconds by the homepage ticker / live rate widgets.
    """
    cached = cache.get('crypto_prices_batch')
    if cached:
        return JsonResponse(cached)

    symbol_map = {
        'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana', 'USDT': 'tether',
        'BNB': 'binancecoin', 'XRP': 'ripple', 'ADA': 'cardano', 'DOGE': 'dogecoin',
        'AVAX': 'avalanche-2', 'LTC': 'litecoin', 'MATIC': 'matic-network',
    }
    fallback_prices = {
        'BTC': 102000.0, 'ETH': 3350.0, 'SOL': 158.0, 'USDT': 1.0,
        'BNB': 943.0, 'XRP': 2.23, 'ADA': 0.53, 'DOGE': 0.163,
        'AVAX': 38.0, 'LTC': 105.0, 'MATIC': 0.55,
    }

    prices = {}
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(symbol_map.values())}&vs_currencies=usd"
        response = requests.get(url, timeout=6)
        response.raise_for_status()
        data = response.json()
        for symbol, coin_id in symbol_map.items():
            if coin_id in data and 'usd' in data[coin_id]:
                prices[symbol] = float(data[coin_id]['usd'])
            else:
                prices[symbol] = fallback_prices[symbol]
    except Exception as e:
        logger.error(f"Error fetching batched crypto prices: {e}")
        prices = dict(fallback_prices)

    cache.set('crypto_prices_batch', prices, 20)
    return JsonResponse(prices)


# ============================================
# ENHANCED CHAT SUPPORT VIEWS
# ============================================

@login_required
def get_or_create_active_chat(request):
    """Get or create active chat session - only one active chat per user"""
    # Get or create the active chat
    chat, created = SupportChat.objects.get_or_create(
        user=request.user,
        status='ACTIVE',
        defaults={'created_at': timezone.now()}
    )
    
    # Get all messages
    chat_messages = chat.messages.all().values(
        'id', 'sender_type', 'sender_name', 'message', 'created_at', 'is_read'
    )
    
    # Mark user's messages as read
    chat.messages.filter(sender_type='SUPPORT', is_read=False).update(is_read=True)
    
    return JsonResponse({
        'chat_id': chat.id,
        'messages': list(chat_messages),
        'created': created,
        'chat_status': chat.status
    })


@login_required
def send_support_message(request):
    """Send a message in support chat"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
            
            if not message_text:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Get or create active chat
            chat, created = SupportChat.objects.get_or_create(
                user=request.user,
                status='ACTIVE'
            )
            
            # Create user message
            SupportMessage.objects.create(
                chat=chat,
                sender_type='USER',
                sender_name=request.user.username,
                message=message_text,
                is_read=False
            )
            
            # Optional: Auto-reply for immediate response
            auto_reply = get_auto_reply(message_text)
            if auto_reply:
                SupportMessage.objects.create(
                    chat=chat,
                    sender_type='SUPPORT',
                    sender_name='Support Bot',
                    message=auto_reply,
                    is_read=False
                )
            
            # Get all messages
            chat_messages = chat.messages.all().values(
                'id', 'sender_type', 'sender_name', 'message', 'created_at', 'is_read'
            )
            
            return JsonResponse({
                'success': True,
                'messages': list(chat_messages)
            })
            
        except Exception as e:
            logger.error(f"Error sending support message: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def get_chat_messages(request):
    """Get all messages from active chat - used for polling"""
    try:
        chat = SupportChat.objects.filter(
            user=request.user,
            status='ACTIVE'
        ).first()
        
        if not chat:
            return JsonResponse({'messages': [], 'chat_status': 'NO_ACTIVE_CHAT'})
        
        # Mark support messages as read
        chat.messages.filter(sender_type='SUPPORT', is_read=False).update(is_read=True)
        
        chat_messages = chat.messages.all().values(
            'id', 'sender_type', 'sender_name', 'message', 'created_at', 'is_read'
        )
        
        return JsonResponse({
            'chat_id': chat.id,
            'messages': list(chat_messages),
            'chat_status': chat.status
        })
        
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def clear_support_chat(request):
    """User closes current chat - admin can still see closed chats"""
    if request.method == 'POST':
        try:
            # Close active chat (don't delete)
            SupportChat.objects.filter(
                user=request.user,
                status='ACTIVE'
            ).update(status='CLOSED', closed_at=timezone.now())
            
            # Create new active chat
            new_chat = SupportChat.objects.create(
                user=request.user,
                status='ACTIVE'
            )
            
            # Welcome message
            SupportMessage.objects.create(
                chat=new_chat,
                sender_type='SUPPORT',
                sender_name='Support Team',
                message='Hello! Welcome to Mirrorwavetrades support. How can we help you today?',
                is_read=False
            )
            
            chat_messages = new_chat.messages.all().values(
                'id', 'sender_type', 'sender_name', 'message', 'created_at', 'is_read'
            )
            
            return JsonResponse({
                'success': True,
                'chat_id': new_chat.id,
                'messages': list(chat_messages)
            })
            
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def get_auto_reply(message):
    """Generate automatic replies based on keywords (optional)"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['deposit', 'payment', 'fund']):
        return "To make a deposit, navigate to Dashboard > Deposit. We support Bitcoin, Ethereum, Solana, and other major cryptocurrencies. Deposits are processed within 10-30 minutes after confirmation."
    
    elif any(word in message_lower for word in ['withdrawal', 'withdraw', 'cashout']):
        return "For withdrawals, go to Dashboard > Withdrawal. Please ensure your account is verified and withdrawal is approved by admin. Minimum withdrawal is $50. Processing time is 24-48 hours."
    
    elif any(word in message_lower for word in ['trading bot', 'bot', 'automated']):
        return "Our Trading Bots offer automated trading with daily profits. Visit Trading Bot section to view available plans: Basic, Intermediate, Advanced, and Pro with different profit percentages."
    
    elif any(word in message_lower for word in ['copy trading', 'copy trade', 'follow trader']):
        return "Copy Trading allows you to automatically copy trades from professional traders. Visit the Copy Trading section to browse top traders and their performance metrics."
    
    elif any(word in message_lower for word in ['invest', 'investment', 'plan']):
        return "We offer investment plans ranging from Starter to Diamond tier with guaranteed ROI over fixed durations. Visit the Investment Plans section to browse available options."

    elif any(word in message_lower for word in ['verification', 'verify', 'kyc']):
        return "Account verification is handled by our admin team. Your account will be reviewed within 24 hours. You will receive an email notification once approved."
    
    elif any(word in message_lower for word in ['help', 'support', 'assistance']):
        return "I am here to help! You can ask about deposits, withdrawals, trading bots, copy trading, investment plans, or any other features. Our support team will respond shortly if you need personalized assistance."
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! Thank you for contacting Mirrorwavetrades support. How can I assist you today?"
    
    # Return None if no auto-reply needed - admin will respond manually
    return None

# ============================================================
# PRODUCT PAGES
# ============================================================

def stocks(request):
    """Stocks product page"""
    return render(request, 'stocks.html')


def crypto(request):
    """Crypto product page"""
    return render(request, 'crypto.html')


def forex(request):
    """Forex product page"""
    return render(request, 'forex.html')


def options(request):
    """Options product page"""
    return render(request, 'options.html')


# ============================================================
# COMPANY PAGES
# ============================================================

def about(request):
    """About Us page"""
    return render(request, 'about.html')


def contact(request):
    """Contact page — handles GET and POST (form submission)"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        subject    = request.POST.get('subject', '').strip()
        message    = request.POST.get('message', '').strip()

        if all([first_name, last_name, email, subject, message]):
            logger.info(
                f"Contact form submitted: {first_name} {last_name} <{email}> — {subject}"
            )
            messages.success(
                request,
                "Thank you for reaching out! Our team will reply within 2 hours."
            )
        else:
            messages.error(request, "Please fill in all required fields.")

        return redirect('contact')

    return render(request, 'contact.html')


def careers(request):
    """Careers page"""
    return render(request, 'careers.html')


def press(request):
    """Press / media page"""
    return render(request, 'press.html')


# ============================================================
# LEGAL PAGES
# ============================================================

def privacy_policy(request):
    """Privacy Policy page"""
    return render(request, 'privacy_policy.html')


def terms_of_service(request):
    """Terms of Service page"""
    return render(request, 'terms_of_service.html')


def cookie_policy(request):
    """Cookie Policy page"""
    return render(request, 'cookie_policy.html')


def disclaimer(request):
    """Disclaimer page"""
    return render(request, 'disclaimer.html')