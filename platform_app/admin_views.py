# Create this file: platform_app/admin_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .models import (
    User, WalletAddress, TradingBotPlan, UserBotSubscription,
    CopyTrader, CopyTradingSubscription, Transaction, Portfolio,
    Trade, PlatformSettings, SupportChat, SupportMessage,
    UserActivity, AdminUser, SystemLog,
    InvestmentPlan, UserInvestment,
)


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@user_passes_test(is_admin)
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    # Get date range for filtering
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User statistics
    total_users = User.objects.count()
    new_users_today = User.objects.filter(created_at__date=today).count()
    new_users_week = User.objects.filter(created_at__date__gte=week_ago).count()
    active_users = User.objects.filter(last_login__gte=week_ago).count()
    
    # Financial statistics
    total_deposits = Transaction.objects.filter(
        transaction_type='DEPOSIT', 
        status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = Transaction.objects.filter(
        transaction_type='WITHDRAWAL',
        status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_deposits = Transaction.objects.filter(
        transaction_type='DEPOSIT',
        status='PENDING'
    ).count()
    
    pending_withdrawals = Transaction.objects.filter(
        transaction_type='WITHDRAWAL',
        status='PENDING'
    ).count()
    
    # Trading statistics
    total_trades = Trade.objects.count()
    active_bots = UserBotSubscription.objects.filter(is_active=True).count()
    active_copy_trades = CopyTradingSubscription.objects.filter(is_active=True).count()
    
    # Support statistics
    open_chats = SupportChat.objects.filter(status='ACTIVE').count()
    unread_messages = SupportMessage.objects.filter(
        sender_type='USER',
        is_read=False
    ).count()
    
    # Recent activities
    recent_activities = UserActivity.objects.select_related('user')[:20]
    
    # Recent transactions
    recent_transactions = Transaction.objects.select_related('user').order_by('-created_at')[:10]
    
    # Chart data - User registrations over time
    user_chart_data = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        count = User.objects.filter(created_at__date=date).count()
        user_chart_data.append({
            'date': date.strftime('%b %d'),
            'count': count
        })
    
    # Revenue chart data
    revenue_chart_data = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        deposits = Transaction.objects.filter(
            transaction_type='DEPOSIT',
            status='APPROVED',
            created_at__date=date
        ).aggregate(total=Sum('amount'))['total'] or 0
        revenue_chart_data.append({
            'date': date.strftime('%b %d'),
            'amount': float(deposits)
        })
    
    context = {
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'active_users': active_users,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'pending_deposits': pending_deposits,
        'pending_withdrawals': pending_withdrawals,
        'total_trades': total_trades,
        'active_bots': active_bots,
        'active_copy_trades': active_copy_trades,
        'open_chats': open_chats,
        'unread_messages': unread_messages,
        'recent_activities': recent_activities,
        'recent_transactions': recent_transactions,
        'user_chart_data': json.dumps(user_chart_data),
        'revenue_chart_data': json.dumps(revenue_chart_data),
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


@user_passes_test(is_admin)
def admin_users_list(request):
    """List all users with search and filter"""
    search = request.GET.get('search', '')
    status = request.GET.get('status', 'all')
    
    users = User.objects.all().order_by('-created_at')
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(legal_first_name__icontains=search) |
            Q(legal_last_name__icontains=search)
        )
    
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'withdrawal_approved':
        users = users.filter(withdrawal_approved=True)
    
    context = {
        'users': users,
        'search': search,
        'status': status,
    }
    
    return render(request, 'custom_admin/users_list.html', context)


@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    """View and edit user details"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_balance':
            amount = Decimal(request.POST.get('amount', 0))
            user.account_balance = amount
            user.save()
            
            SystemLog.objects.create(
                level='INFO',
                action='UPDATE_USER_BALANCE',
                description=f'Admin updated balance for {user.username} to ${amount}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Balance updated to ${amount}')
        
        elif action == 'toggle_withdrawal':
            user.withdrawal_approved = not user.withdrawal_approved
            user.save()
            
            status = 'approved' if user.withdrawal_approved else 'disapproved'
            SystemLog.objects.create(
                level='INFO',
                action='TOGGLE_WITHDRAWAL',
                description=f'Admin {status} withdrawal for {user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Withdrawal {status}')
        
        elif action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()

            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {status}')

        elif action == 'update_profile':
            user.legal_first_name = request.POST.get('legal_first_name', user.legal_first_name).strip()
            user.legal_last_name = request.POST.get('legal_last_name', user.legal_last_name).strip()
            user.email = request.POST.get('email', user.email).strip()
            user.preferred_currency = request.POST.get('preferred_currency', user.preferred_currency)
            user.bonus = Decimal(request.POST.get('bonus') or 0)
            user.commission = Decimal(request.POST.get('commission') or 0)
            user.save()

            SystemLog.objects.create(
                level='INFO',
                action='UPDATE_USER_PROFILE',
                description=f'Admin updated profile for {user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )

            messages.success(request, 'Profile updated successfully')

        elif action == 'toggle_staff':
            if user.id == request.user.id:
                messages.error(request, "You can't change your own admin status.")
            else:
                user.is_staff = not user.is_staff
                if not user.is_staff:
                    user.is_superuser = False
                user.save()

                status = 'granted' if user.is_staff else 'revoked'
                SystemLog.objects.create(
                    level='WARNING',
                    action='TOGGLE_ADMIN_ACCESS',
                    description=f'Admin {status} admin access for {user.username}',
                    user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                messages.success(request, f'Admin access {status} for {user.username}')

        elif action == 'delete_user':
            if user.id == request.user.id:
                messages.error(request, "You can't delete your own account.")
                return redirect('admin_user_detail', user_id=user_id)

            username = user.username
            SystemLog.objects.create(
                level='CRITICAL',
                action='DELETE_USER',
                description=f'Admin deleted user account {username} (id={user.id})',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            user.delete()
            messages.success(request, f'User {username} deleted permanently')
            return redirect('admin_users_list')

        return redirect('admin_user_detail', user_id=user_id)
    
    # Get user statistics
    user_transactions = Transaction.objects.filter(user=user).order_by('-created_at')[:20]
    user_trades = Trade.objects.filter(user=user).order_by('-created_at')[:20]
    user_activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:50]
    
    context = {
        'user_obj': user,
        'user_transactions': user_transactions,
        'user_trades': user_trades,
        'user_activities': user_activities,
    }
    
    return render(request, 'custom_admin/user_detail.html', context)


@user_passes_test(is_admin)
def admin_transactions_list(request):
    """List and manage transactions"""
    status = request.GET.get('status', 'all')
    trans_type = request.GET.get('type', 'all')

    transactions = Transaction.objects.select_related('user').order_by('-created_at')

    if status != 'all':
        transactions = transactions.filter(status=status.upper())

    if trans_type != 'all':
        transactions = transactions.filter(transaction_type=trans_type.upper())

    today = timezone.now().date()
    pending_count = Transaction.objects.filter(status='PENDING').count()
    approved_today = Transaction.objects.filter(status='APPROVED', updated_at__date=today).count()
    total_deposits = Transaction.objects.filter(
        transaction_type='DEPOSIT', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_withdrawals = Transaction.objects.filter(
        transaction_type='WITHDRAWAL', status='APPROVED'
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'transactions': transactions,
        'status': status,
        'trans_type': trans_type,
        'pending_count': pending_count,
        'approved_today': approved_today,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
    }

    return render(request, 'custom_admin/transactions_list.html', context)


@user_passes_test(is_admin)
def admin_transaction_action(request, transaction_id):
    """Approve or reject transaction"""
    if request.method == 'POST':
        transaction = get_object_or_404(Transaction, id=transaction_id)
        action = request.POST.get('action')
        
        if action == 'approve' and transaction.status == 'PENDING':
            transaction.status = 'APPROVED'
            user = transaction.user
            
            if transaction.transaction_type == 'DEPOSIT':
                user.account_balance += transaction.amount
                user.total_deposit += transaction.amount
                user.save()
            elif transaction.transaction_type == 'WITHDRAWAL':
                if user.account_balance >= transaction.amount:
                    user.account_balance -= transaction.amount
                    user.total_withdrawal += transaction.amount
                    user.save()
            
            transaction.save()
            
            SystemLog.objects.create(
                level='INFO',
                action='APPROVE_TRANSACTION',
                description=f'Admin approved {transaction.transaction_type} of ${transaction.amount} for {user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Transaction approved successfully')
        
        elif action == 'reject':
            transaction.status = 'REJECTED'
            transaction.save()
            
            SystemLog.objects.create(
                level='WARNING',
                action='REJECT_TRANSACTION',
                description=f'Admin rejected {transaction.transaction_type} of ${transaction.amount} for {transaction.user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Transaction rejected')
        
        return redirect('admin_transactions_list')
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@user_passes_test(is_admin)
def admin_traders_list(request):
    """Manage copy traders"""
    traders = CopyTrader.objects.all().order_by('-created_at')
    
    context = {'traders': traders}
    return render(request, 'custom_admin/traders_list.html', context)


@user_passes_test(is_admin)
def admin_trader_create(request):
    """Create new copy trader"""
    if request.method == 'POST':
        name = request.POST.get('name')
        country = request.POST.get('country')
        country_flag = request.POST.get('country_flag')
        rating = Decimal(request.POST.get('rating'))
        profit_percentage = Decimal(request.POST.get('profit_percentage'))
        roi = Decimal(request.POST.get('roi'))
        commission = Decimal(request.POST.get('commission'))
        profile_image = request.FILES.get('profile_image')
        
        trader = CopyTrader.objects.create(
            name=name,
            country=country,
            country_flag=country_flag,
            rating=rating,
            profit_percentage_per_day=profit_percentage,
            roi=roi,
            commission_percentage=commission,
            profile_image=profile_image
        )
        
        messages.success(request, f'Trader {name} created successfully')
        return redirect('admin_traders_list')
    
    return render(request, 'custom_admin/trader_form.html', {'action': 'create'})


@user_passes_test(is_admin)
def admin_trader_edit(request, trader_id):
    """Edit copy trader"""
    trader = get_object_or_404(CopyTrader, id=trader_id)
    
    if request.method == 'POST':
        trader.name = request.POST.get('name')
        trader.country = request.POST.get('country')
        trader.country_flag = request.POST.get('country_flag')
        trader.rating = Decimal(request.POST.get('rating'))
        trader.profit_percentage_per_day = Decimal(request.POST.get('profit_percentage'))
        trader.roi = Decimal(request.POST.get('roi'))
        trader.commission_percentage = Decimal(request.POST.get('commission'))
        
        if 'profile_image' in request.FILES:
            trader.profile_image = request.FILES['profile_image']
        
        trader.save()
        
        messages.success(request, 'Trader updated successfully')
        return redirect('admin_traders_list')
    
    context = {'trader': trader, 'action': 'edit'}
    return render(request, 'custom_admin/trader_form.html', context)


@user_passes_test(is_admin)
def admin_trader_delete(request, trader_id):
    """Delete copy trader"""
    if request.method == 'POST':
        trader = get_object_or_404(CopyTrader, id=trader_id)
        trader_name = trader.name
        trader.delete()
        
        messages.success(request, f'Trader {trader_name} deleted successfully')
        return redirect('admin_traders_list')
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@user_passes_test(is_admin)
def admin_bot_plans_list(request):
    """Manage trading bot plans"""
    plans = TradingBotPlan.objects.all().order_by('price')

    context = {'plans': plans}
    return render(request, 'custom_admin/bot_plans_list.html', context)


def _save_bot_plan(request, plan):
    """Parse POST data and create/update a TradingBotPlan.

    Returns an error message string if the save was rejected (e.g. duplicate
    plan_type), or None on success.
    """
    data = request.POST
    raw_features = data.get('features_text', '')
    features = [line.strip() for line in raw_features.splitlines() if line.strip()]

    plan_type = data.get('plan_type', 'BASIC')
    dupe = TradingBotPlan.objects.filter(plan_type=plan_type)
    if plan is not None:
        dupe = dupe.exclude(id=plan.id)
    if dupe.exists():
        return f'A "{plan_type}" plan already exists. Edit that one instead, or choose a different type.'

    fields = dict(
        plan_type=plan_type,
        price=Decimal(data.get('price', '0')),
        daily_profit_percentage=Decimal(data.get('daily_profit_percentage', '0')),
        features=features,
        is_active=bool(data.get('is_active')),
    )

    if plan is None:
        TradingBotPlan.objects.create(**fields)
    else:
        for attr, val in fields.items():
            setattr(plan, attr, val)
        plan.save()
    return None


@user_passes_test(is_admin)
def admin_bot_plan_create(request):
    """Create a new trading bot plan."""
    if request.method == 'POST':
        error = _save_bot_plan(request, plan=None)
        if error:
            messages.error(request, error)
            context = {'plan': None, 'action': 'create', 'plan_choices': TradingBotPlan.PLAN_CHOICES}
            return render(request, 'custom_admin/bot_plan_form.html', context)
        messages.success(request, 'Bot plan created successfully.')
        return redirect('admin_bot_plans_list')

    context = {'plan': None, 'action': 'create', 'plan_choices': TradingBotPlan.PLAN_CHOICES}
    return render(request, 'custom_admin/bot_plan_form.html', context)


@user_passes_test(is_admin)
def admin_bot_plan_edit(request, plan_id):
    """Edit an existing trading bot plan."""
    plan = get_object_or_404(TradingBotPlan, id=plan_id)

    if request.method == 'POST':
        error = _save_bot_plan(request, plan=plan)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f'Bot plan "{plan.plan_type}" updated successfully.')
            return redirect('admin_bot_plans_list')

    context = {'plan': plan, 'action': 'edit', 'plan_choices': TradingBotPlan.PLAN_CHOICES}
    return render(request, 'custom_admin/bot_plan_form.html', context)


@user_passes_test(is_admin)
def admin_bot_plan_delete(request, plan_id):
    """Delete a trading bot plan."""
    if request.method == 'POST':
        plan = get_object_or_404(TradingBotPlan, id=plan_id)
        plan_type = plan.plan_type
        plan.delete()
        messages.success(request, f'Bot plan "{plan_type}" deleted successfully.')
        return redirect('admin_bot_plans_list')
    return JsonResponse({'error': 'Invalid request'}, status=400)


@user_passes_test(is_admin)
def admin_bot_plan_toggle(request, plan_id):
    """Toggle active/inactive status of a trading bot plan."""
    if request.method == 'POST':
        plan = get_object_or_404(TradingBotPlan, id=plan_id)
        plan.is_active = not plan.is_active
        plan.save()
        status = 'activated' if plan.is_active else 'deactivated'
        messages.success(request, f'Bot plan "{plan.plan_type}" {status}.')
    return redirect('admin_bot_plans_list')


# ── Investment Plans Admin Views ──────────────────────────────────────────────

@user_passes_test(is_admin)
def admin_investment_plans_list(request):
    """List all investment plans with key stats."""
    plans = InvestmentPlan.objects.prefetch_related('subscriptions').order_by('minimum_amount')

    total_investments = UserInvestment.objects.count()
    total_invested    = UserInvestment.objects.aggregate(
        total=Sum('amount_invested')
    )['total'] or Decimal('0')
    active_count      = plans.filter(is_active=True).count()

    context = {
        'plans':             plans,
        'active_count':      active_count,
        'total_investments': total_investments,
        'total_invested':    total_invested,
    }
    return render(request, 'custom_admin/investment_plans_list.html', context)


@user_passes_test(is_admin)
def admin_investment_plan_create(request):
    """Create a new investment plan."""
    if request.method == 'POST':
        error = _save_investment_plan(request, plan=None)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, 'Investment plan created successfully.')
            return redirect('admin_investment_plans_list')

    context = {
        'plan':         None,
        'tier_choices': InvestmentPlan.PLAN_TIER_CHOICES,
    }
    return render(request, 'custom_admin/investment_plan_form.html', context)


@user_passes_test(is_admin)
def admin_investment_plan_edit(request, plan_id):
    """Edit an existing investment plan."""
    plan = get_object_or_404(InvestmentPlan, id=plan_id)

    if request.method == 'POST':
        error = _save_investment_plan(request, plan=plan)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, f'Plan "{plan.name}" updated successfully.')
            return redirect('admin_investment_plans_list')

    context = {
        'plan':         plan,
        'tier_choices': InvestmentPlan.PLAN_TIER_CHOICES,
    }
    return render(request, 'custom_admin/investment_plan_form.html', context)


@user_passes_test(is_admin)
def admin_investment_plan_toggle(request, plan_id):
    """Toggle active/inactive status of an investment plan."""
    if request.method == 'POST':
        plan = get_object_or_404(InvestmentPlan, id=plan_id)
        plan.is_active = not plan.is_active
        plan.save()
        status = 'activated' if plan.is_active else 'deactivated'
        messages.success(request, f'Plan "{plan.name}" {status}.')
    return redirect('admin_investment_plans_list')


@user_passes_test(is_admin)
def admin_investment_plan_delete(request, plan_id):
    """Delete an investment plan."""
    if request.method == 'POST':
        plan = get_object_or_404(InvestmentPlan, id=plan_id)
        if plan.subscriptions.filter(status='ACTIVE').exists():
            messages.error(request, f'Cannot delete "{plan.name}" — it has active subscriptions. Disable it instead.')
        else:
            name = plan.name
            plan.delete()
            messages.success(request, f'Plan "{name}" deleted successfully.')
    return redirect('admin_investment_plans_list')


def _save_investment_plan(request, plan):
    """Parse POST data and create/update an InvestmentPlan.

    Returns an error message string if the save was rejected (e.g. duplicate
    tier), or None on success.
    """
    data = request.POST

    tier = data.get('tier', 'STARTER')
    dupe = InvestmentPlan.objects.filter(tier=tier)
    if plan is not None:
        dupe = dupe.exclude(id=plan.id)
    if dupe.exists():
        return f'A "{tier}" plan already exists. Edit that one instead, or choose a different tier.'

    # Parse features: one per line
    raw_features = data.get('features_text', '')
    features = [line.strip() for line in raw_features.splitlines() if line.strip()]

    # Parse maximum_amount (optional)
    max_raw = data.get('maximum_amount', '').strip()
    maximum_amount = Decimal(max_raw) if max_raw else None

    fields = dict(
        name           = data.get('name', '').strip(),
        tier           = data.get('tier', 'STARTER'),
        description    = data.get('description', '').strip(),
        minimum_amount = Decimal(data.get('minimum_amount', '0')),
        maximum_amount = maximum_amount,
        roi_percentage = Decimal(data.get('roi_percentage', '0')),
        duration_days  = int(data.get('duration_days', 1)),
        risk_level     = data.get('risk_level', 'MEDIUM'),
        features       = features,
        is_active      = bool(data.get('is_active')),
        is_featured    = bool(data.get('is_featured')),
    )

    if plan is None:
        InvestmentPlan.objects.create(**fields)
    else:
        for attr, val in fields.items():
            setattr(plan, attr, val)
        plan.save()
    return None


# ── Support Chats ─────────────────────────────────────────────────────────────

@user_passes_test(is_admin)
def admin_support_chats(request):
    """Manage support chats"""
    status = request.GET.get('status', 'all')
    
    chats = SupportChat.objects.select_related('user').annotate(
        message_count=Count('messages'),
        unread_count=Count('messages', filter=Q(messages__is_read=False, messages__sender_type='USER'))
    ).order_by('-updated_at')
    
    if status == 'active':
        chats = chats.filter(status='ACTIVE')
    elif status == 'closed':
        chats = chats.filter(status='CLOSED')
    
    context = {
        'chats': chats,
        'status': status,
    }
    
    return render(request, 'custom_admin/support_chats.html', context)


@user_passes_test(is_admin)
def admin_chat_detail(request, chat_id):
    """View and reply to support chat"""
    chat = get_object_or_404(SupportChat, id=chat_id)
    
    if request.method == 'POST':
        message = request.POST.get('message')
        
        if message:
            SupportMessage.objects.create(
                chat=chat,
                sender_type='SUPPORT',
                sender_name=f'{request.user.first_name} {request.user.last_name}' if request.user.first_name else request.user.username,
                message=message,
                is_read=False
            )
            
            # Mark user messages as read
            chat.messages.filter(sender_type='USER', is_read=False).update(is_read=True)
            
            messages.success(request, 'Reply sent successfully')
            return redirect('admin_chat_detail', chat_id=chat_id)
    
    messages_list = chat.messages.all().order_by('created_at')
    
    context = {
        'chat': chat,
        'messages_list': messages_list,
    }
    
    return render(request, 'custom_admin/chat_detail.html', context)


@user_passes_test(is_admin)
def admin_activities_list(request):
    """View all user activities"""
    user_filter = request.GET.get('user', '')
    action_type = request.GET.get('action', 'all')
    
    activities = UserActivity.objects.select_related('user').order_by('-timestamp')
    
    if user_filter:
        activities = activities.filter(user__username__icontains=user_filter)
    
    if action_type != 'all':
        activities = activities.filter(action_type=action_type.upper())
    
    # Get statistics
    today = timezone.now().date()
    today_count = UserActivity.objects.filter(timestamp__date=today).count()
    
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    recent_count = UserActivity.objects.filter(timestamp__gte=five_minutes_ago).count()
    
    # Count unique users
    unique_users_count = UserActivity.objects.values('user').distinct().count()
    
    # Limit results for performance
    activities = activities[:200]
    
    context = {
        'activities': activities,
        'user_filter': user_filter,
        'action_type': action_type,
        'today_count': today_count,
        'recent_count': recent_count,
        'unique_users': unique_users_count,
    }
    
    return render(request, 'custom_admin/activities_list.html', context)


@user_passes_test(is_admin)
def admin_settings(request):
    """Platform settings"""
    settings, created = PlatformSettings.objects.get_or_create(id=1)
    wallets = WalletAddress.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_settings':
            settings.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
            settings.minimum_deposit = Decimal(request.POST.get('minimum_deposit'))
            settings.minimum_withdrawal = Decimal(request.POST.get('minimum_withdrawal'))
            settings.trading_fee_percentage = Decimal(request.POST.get('trading_fee'))
            settings.withdrawal_fee_percentage = Decimal(request.POST.get('withdrawal_fee'))
            settings.save()
            
            messages.success(request, 'Settings updated successfully')
        
        elif action == 'add_wallet':
            cryptocurrency = request.POST.get('cryptocurrency')
            wallet_address = request.POST.get('wallet_address')

            if WalletAddress.objects.filter(cryptocurrency=cryptocurrency).exists():
                messages.error(request, f'A {cryptocurrency} wallet already exists. Edit it instead of adding a new one.')
            else:
                WalletAddress.objects.create(
                    cryptocurrency=cryptocurrency,
                    wallet_address=wallet_address
                )
                messages.success(request, f'{cryptocurrency} wallet added successfully')

        return redirect('admin_settings')

    context = {
        'settings': settings,
        'wallets': wallets,
    }

    return render(request, 'custom_admin/settings.html', context)


@user_passes_test(is_admin)
def admin_wallet_edit(request, wallet_id):
    """Edit a company wallet address."""
    wallet = get_object_or_404(WalletAddress, id=wallet_id)
    if request.method == 'POST':
        wallet.wallet_address = request.POST.get('wallet_address', wallet.wallet_address).strip()
        wallet.save()
        messages.success(request, f'{wallet.cryptocurrency} wallet updated successfully.')
    return redirect('admin_settings')


@user_passes_test(is_admin)
def admin_wallet_delete(request, wallet_id):
    """Delete a company wallet address."""
    if request.method == 'POST':
        wallet = get_object_or_404(WalletAddress, id=wallet_id)
        crypto = wallet.cryptocurrency
        wallet.delete()
        messages.success(request, f'{crypto} wallet deleted successfully.')
    return redirect('admin_settings')


@user_passes_test(is_admin)
def admin_wallet_toggle(request, wallet_id):
    """Toggle active/inactive status of a company wallet address."""
    if request.method == 'POST':
        wallet = get_object_or_404(WalletAddress, id=wallet_id)
        wallet.is_active = not wallet.is_active
        wallet.save()
        status = 'activated' if wallet.is_active else 'deactivated'
        messages.success(request, f'{wallet.cryptocurrency} wallet {status}.')
    return redirect('admin_settings')


@user_passes_test(is_admin)
def admin_admins_list(request):
    """List admin/staff accounts and promote/revoke access."""
    admins = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).order_by('-is_superuser', 'username')

    context = {'admins': admins}
    return render(request, 'custom_admin/admins_list.html', context)


@user_passes_test(is_admin)
def admin_promote_user(request):
    """Grant admin (staff) access to an existing user by username or email."""
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        make_superuser = bool(request.POST.get('make_superuser'))

        user = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        if not user:
            messages.error(request, f'No user found matching "{identifier}".')
        else:
            user.is_staff = True
            if make_superuser:
                user.is_superuser = True
            user.save()

            SystemLog.objects.create(
                level='WARNING',
                action='PROMOTE_ADMIN',
                description=f'Admin granted {"super admin" if make_superuser else "admin"} access to {user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'{user.username} is now an admin.')

    return redirect('admin_admins_list')


@user_passes_test(is_admin)
def admin_revoke_admin(request, user_id):
    """Revoke admin (staff/superuser) access from a user."""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if user.id == request.user.id:
            messages.error(request, "You can't revoke your own admin access.")
        else:
            user.is_staff = False
            user.is_superuser = False
            user.save()

            SystemLog.objects.create(
                level='WARNING',
                action='REVOKE_ADMIN',
                description=f'Admin revoked admin access from {user.username}',
                user=request.user,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Admin access revoked for {user.username}.')

    return redirect('admin_admins_list')


# ── Transactions: create / delete ─────────────────────────────────────────────

@user_passes_test(is_admin)
def admin_transaction_create(request):
    """Manually log a transaction for a user (e.g. a correction or bonus credit)."""
    if request.method == 'POST':
        target = request.POST.get('username', '').strip()
        user = User.objects.filter(Q(username__iexact=target) | Q(email__iexact=target)).first()

        if not user:
            messages.error(request, f'No user found matching "{target}".')
            return redirect('admin_transactions_list')

        transaction_type = request.POST.get('transaction_type', 'DEPOSIT')
        amount = Decimal(request.POST.get('amount', '0'))
        status = request.POST.get('status', 'PENDING')
        description = request.POST.get('description', '').strip()

        transaction = Transaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            status=status,
            description=description or f'Manually created by admin {request.user.username}',
        )

        # Apply the same balance effects as the approve() flow when created as already-settled.
        if status in ('APPROVED', 'COMPLETED'):
            if transaction_type == 'DEPOSIT':
                user.account_balance += amount
                user.total_deposit += amount
                user.save()
            elif transaction_type == 'WITHDRAWAL' and user.account_balance >= amount:
                user.account_balance -= amount
                user.total_withdrawal += amount
                user.save()
            elif transaction_type in ('BONUS', 'PROFIT'):
                user.account_balance += amount
                user.save()

        SystemLog.objects.create(
            level='INFO',
            action='CREATE_TRANSACTION',
            description=f'Admin manually created {transaction_type} of ${amount} for {user.username}',
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f'Transaction created for {user.username}.')
    return redirect('admin_transactions_list')


@user_passes_test(is_admin)
def admin_transaction_delete(request, transaction_id):
    """Delete a transaction record. Only allowed while still PENDING, so no
    balance change ever needs to be reversed."""
    if request.method == 'POST':
        transaction = get_object_or_404(Transaction, id=transaction_id)
        if transaction.status != 'PENDING':
            messages.error(request, 'Only pending transactions can be deleted. Reject it first if needed.')
        else:
            transaction.delete()
            messages.success(request, 'Transaction deleted.')
    return redirect('admin_transactions_list')


# ── Support chats: close / delete ─────────────────────────────────────────────

@user_passes_test(is_admin)
def admin_chat_close(request, chat_id):
    """Toggle a support chat between ACTIVE and CLOSED."""
    if request.method == 'POST':
        chat = get_object_or_404(SupportChat, id=chat_id)
        if chat.status == 'ACTIVE':
            chat.status = 'CLOSED'
            chat.closed_at = timezone.now()
        else:
            chat.status = 'ACTIVE'
            chat.closed_at = None
        chat.save()
        messages.success(request, f'Chat #{chat.id} marked as {chat.status.title()}.')
        return redirect('admin_chat_detail', chat_id=chat_id)
    return redirect('admin_support_chats')


@user_passes_test(is_admin)
def admin_chat_delete(request, chat_id):
    """Permanently delete a support chat and its messages."""
    if request.method == 'POST':
        chat = get_object_or_404(SupportChat, id=chat_id)
        chat.delete()
        messages.success(request, f'Chat #{chat_id} deleted.')
    return redirect('admin_support_chats')


@user_passes_test(is_admin)
def admin_system_logs(request):
    """View system logs"""
    level = request.GET.get('level', 'all')
    
    logs = SystemLog.objects.select_related('user').order_by('-timestamp')
    
    if level != 'all':
        logs = logs.filter(level=level.upper())
    
    logs = logs[:200]
    
    context = {
        'logs': logs,
        'level': level,
    }
    
    return render(request, 'custom_admin/system_logs.html', context)