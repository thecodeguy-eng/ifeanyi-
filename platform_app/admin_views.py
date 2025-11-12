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
    UserActivity, AdminUser, SystemLog
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
    
    context = {
        'transactions': transactions,
        'status': status,
        'trans_type': trans_type,
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
    from datetime import timedelta
    from django.db.models import Count
    
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