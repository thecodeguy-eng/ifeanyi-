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
import logging
from django.utils import timezone

from .models import (
    User, WalletAddress, TradingBotPlan, UserBotSubscription,
    CopyTrader, CopyTradingSubscription, Transaction, Portfolio,
    Trade, PlatformSettings,SupportChat, SupportMessage
)

# Set up logging
logger = logging.getLogger(__name__)


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
        # Map symbols to CoinGecko IDs
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
        
        coin_id = symbol_map.get(symbol.upper())
        if not coin_id:
            logger.warning(f"Unknown cryptocurrency symbol: {symbol}")
            return Decimal('1')
        
        # Make API request
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        logger.info(f"Fetching price for {symbol} from CoinGecko API")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract price
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
    
    # Fallback prices - November 2025 current market prices
    fallback_prices = {
        'BTC': Decimal('102000'),      # Bitcoin ~$102,000
        'ETH': Decimal('3350'),        # Ethereum ~$3,350
        'SOL': Decimal('158'),         # Solana ~$158
        'USDT': Decimal('1.00'),       # Tether ~$1.00
        'BNB': Decimal('943'),         # BNB ~$943
        'XRP': Decimal('2.23'),        # Ripple ~$2.23
        'ADA': Decimal('0.53'),        # Cardano ~$0.53
        'DOGE': Decimal('0.163'),      # Dogecoin ~$0.163
    }
    
    fallback_price = fallback_prices.get(symbol.upper(), Decimal('1'))
    logger.warning(f"Using fallback price for {symbol}: ${fallback_price}")
    return fallback_price


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
        
        # Get exchange rates using real-time prices
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
        
        # Apply fee to output
        to_amount = to_amount * (1 - (fee_percentage / 100))
        
        # Check balance
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
                # Update average buy price
                total_value = (portfolio_item.amount * portfolio_item.average_buy_price) + (to_amount * current_price)
                portfolio_item.amount += to_amount
                portfolio_item.average_buy_price = total_value / portfolio_item.amount
                portfolio_item.current_value = portfolio_item.amount * current_price
                portfolio_item.save()
        
        request.user.trading_count += 1
        request.user.save()
        
        messages.success(request, f'Trade executed successfully! Received {to_amount:.8f} {to_currency}')
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
        amount = Decimal(request.POST.get('amount', '0'))
        
        if amount < 100:
            messages.error(request, 'Minimum investment is $100')
            return redirect('copy_trading')
        
        request.session['purchase_type'] = 'copy_trade'
        request.session['purchase_id'] = trader_id
        request.session['purchase_amount'] = str(amount)
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
        min_deposit = settings.minimum_deposit if settings else Decimal('500')
        
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
    
    # Get amount from session
    amount = None
    purchase_type = request.session.get('purchase_type', 'deposit')
    
    # Check all possible session keys for amount
    if 'deposit_amount' in request.session:
        amount = Decimal(request.session['deposit_amount'])
    elif 'purchase_amount' in request.session:
        amount = Decimal(request.session['purchase_amount'])
    
    # If no amount found, redirect back
    if amount is None:
        messages.error(request, 'Invalid payment session. Please try again.')
        return redirect('dashboard')
    
    # Calculate crypto amounts using real-time prices
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
        
        # Validate cryptocurrency selection
        if not selected_crypto or selected_crypto not in crypto_amounts:
            messages.error(request, 'Please select a valid cryptocurrency')
            context = {
                'wallet_addresses': wallet_addresses,
                'amount': amount,
                'crypto_amounts': crypto_amounts,
                'purchase_type': purchase_type,
            }
            return render(request, 'payment_page.html', context)
        
        # Validate proof image
        if not proof_image:
            messages.error(request, 'Please upload payment proof screenshot')
            context = {
                'wallet_addresses': wallet_addresses,
                'amount': amount,
                'crypto_amounts': crypto_amounts,
                'purchase_type': purchase_type,
            }
            return render(request, 'payment_page.html', context)
        
        # Get actual crypto amount at time of submission
        crypto_price = get_crypto_price(selected_crypto)
        actual_crypto_amount = amount / crypto_price if crypto_price > 0 else Decimal('0')
        
        # Create transaction
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
        
        # Clear session
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
        
        # Calculate crypto amount using real-time price
        crypto_price = get_crypto_price(crypto_currency)
        crypto_amount = amount / crypto_price if crypto_price > 0 else Decimal('0')
        
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
        
        logger.info(f"Withdrawal requested: User {request.user.username}, Amount ${amount}, Crypto {crypto_amount:.8f} {crypto_currency}")
        
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
        try:
            price = get_crypto_price(symbol)
            prices[symbol] = float(price)
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            prices[symbol] = 0
    
    return JsonResponse(prices)

# Chat Support Views
@login_required
def get_or_create_active_chat(request):
    """Get or create active chat session"""
    chat, created = SupportChat.objects.get_or_create(
        user=request.user,
        status='ACTIVE',
        defaults={'created_at': timezone.now()}
    )
    
    messages = chat.messages.all().values(
        'id', 'sender_type', 'sender_name', 'message', 'created_at'
    )
    
    return JsonResponse({
        'chat_id': chat.id,
        'messages': list(messages),
        'created': created
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
            
            # Create message
            message = SupportMessage.objects.create(
                chat=chat,
                sender_type='USER',
                sender_name=request.user.username,
                message=message_text
            )
            
            # Auto-reply from support (you can customize this)
            auto_reply = get_auto_reply(message_text)
            if auto_reply:
                SupportMessage.objects.create(
                    chat=chat,
                    sender_type='SUPPORT',
                    sender_name='Support Team',
                    message=auto_reply
                )
            
            # Get all messages
            messages = chat.messages.all().values(
                'id', 'sender_type', 'sender_name', 'message', 'created_at'
            )
            
            return JsonResponse({
                'success': True,
                'messages': list(messages)
            })
            
        except Exception as e:
            logger.error(f"Error sending support message: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def get_chat_messages(request):
    """Get all messages from active chat"""
    try:
        chat = SupportChat.objects.filter(
            user=request.user,
            status='ACTIVE'
        ).first()
        
        if not chat:
            return JsonResponse({'messages': []})
        
        messages = chat.messages.all().values(
            'id', 'sender_type', 'sender_name', 'message', 'created_at'
        )
        
        return JsonResponse({
            'chat_id': chat.id,
            'messages': list(messages)
        })
        
    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def clear_support_chat(request):
    """Close current chat and create a new one"""
    if request.method == 'POST':
        try:
            # Close active chats
            SupportChat.objects.filter(
                user=request.user,
                status='ACTIVE'
            ).update(status='CLOSED', closed_at=timezone.now())
            
            # Create new chat
            new_chat = SupportChat.objects.create(
                user=request.user,
                status='ACTIVE'
            )
            
            # Welcome message
            SupportMessage.objects.create(
                chat=new_chat,
                sender_type='SUPPORT',
                sender_name='Support Team',
                message='Hello! Welcome to InfinityinfluxTrading support. How can we help you today?'
            )
            
            messages = new_chat.messages.all().values(
                'id', 'sender_type', 'sender_name', 'message', 'created_at'
            )
            
            return JsonResponse({
                'success': True,
                'chat_id': new_chat.id,
                'messages': list(messages)
            })
            
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def get_auto_reply(message):
    """Generate automatic replies based on keywords"""
    message_lower = message.lower()
    
    # Keyword-based auto replies
    if any(word in message_lower for word in ['deposit', 'payment', 'fund']):
        return "To make a deposit, navigate to Dashboard > Deposit. We support Bitcoin, Ethereum, Solana, and other major cryptocurrencies. Deposits are processed within 10-30 minutes after confirmation."
    
    elif any(word in message_lower for word in ['withdrawal', 'withdraw', 'cashout']):
        return "For withdrawals, go to Dashboard > Withdrawal. Please ensure your account is verified and withdrawal is approved by admin. Minimum withdrawal is $50. Processing time is 24-48 hours."
    
    elif any(word in message_lower for word in ['trading bot', 'bot', 'automated']):
        return "Our Trading Bots offer automated trading with daily profits. Visit Trading Bot section to view available plans: Basic, Intermediate, Advanced, and Pro with different profit percentages."
    
    elif any(word in message_lower for word in ['copy trading', 'copy trade', 'follow trader']):
        return "Copy Trading allows you to automatically copy trades from professional traders. Visit the Copy Trading section to browse top traders and their performance metrics."
    
    elif any(word in message_lower for word in ['verification', 'verify', 'kyc']):
        return "Account verification is handled by our admin team. Your account will be reviewed within 24 hours. You will receive an email notification once approved."
    
    elif any(word in message_lower for word in ['help', 'support', 'assistance']):
        return "I am here to help! You can ask about deposits, withdrawals, trading bots, copy trading, or any other features. Our support team will respond shortly if you need personalized assistance."
    
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! Thank you for contacting InfinityinfluxTrading support. How can I assist you today?"
    
    # Default response for first message or unrecognized queries
    return "Thank you for your message. A support agent will respond to you shortly. In the meantime, you can ask about deposits, withdrawals, trading bots, or copy trading."