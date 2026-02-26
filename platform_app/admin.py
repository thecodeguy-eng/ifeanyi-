from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django import forms
from .models import (
    User, WalletAddress, TradingBotPlan, UserBotSubscription,
    CopyTrader, CopyTradingSubscription, Transaction, Portfolio,
    Trade, PlatformSettings, SupportChat, SupportMessage, PasswordResetCode,
    InvestmentPlan, UserInvestment,
)


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'code', 'is_used', 'is_valid_status', 'created_at', 'expires_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username', 'email', 'code']
    readonly_fields = ['user', 'email', 'code', 'created_at', 'expires_at']
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green; font-weight: bold;">✓ Valid</span>')
        elif obj.is_used:
            return format_html('<span style="color: gray;">✗ Used</span>')
        else:
            return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        return False  # Codes are created programmatically


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'legal_first_name', 'legal_last_name', 
                    'account_balance', 'preferred_currency', 'withdrawal_approved', 'is_active']
    list_filter = ['preferred_currency', 'withdrawal_approved', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'legal_first_name', 'legal_last_name', 'phone_number']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Personal Information', {
            'fields': ('legal_first_name', 'legal_last_name', 'phone_number', 'preferred_currency')
        }),
        ('Account Details', {
            'fields': ('account_balance', 'total_profit', 'bonus', 'commission', 
                      'trading_count', 'total_deposit', 'total_withdrawal', 'withdrawal_approved')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['approve_withdrawal', 'disapprove_withdrawal']
    
    def approve_withdrawal(self, request, queryset):
        queryset.update(withdrawal_approved=True)
        self.message_user(request, f"{queryset.count()} users approved for withdrawal")
    approve_withdrawal.short_description = "Approve withdrawal for selected users"
    
    def disapprove_withdrawal(self, request, queryset):
        queryset.update(withdrawal_approved=False)
        self.message_user(request, f"{queryset.count()} users disapproved for withdrawal")
    disapprove_withdrawal.short_description = "Disapprove withdrawal for selected users"


@admin.register(WalletAddress)
class WalletAddressAdmin(admin.ModelAdmin):
    list_display = ['cryptocurrency', 'wallet_address', 'is_active', 'created_at']
    list_filter = ['cryptocurrency', 'is_active']
    search_fields = ['cryptocurrency', 'wallet_address']


@admin.register(TradingBotPlan)
class TradingBotPlanAdmin(admin.ModelAdmin):
    list_display = ['plan_type', 'price', 'daily_profit_percentage', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['plan_type']


@admin.register(UserBotSubscription)
class UserBotSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'is_active', 'start_date', 'total_earned']
    list_filter = ['plan', 'is_active', 'start_date']
    search_fields = ['user__username', 'user__email']
    raw_id_fields = ['user']


@admin.register(CopyTrader)
class CopyTraderAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'rating', 'profit_percentage_per_day', 
                    'total_trades', 'followers_count', 'roi', 'has_image', 'is_active']
    list_filter = ['country', 'is_active', 'created_at']
    search_fields = ['name', 'country']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'profile_image', 'country', 'country_flag')
        }),
        ('Performance Metrics', {
            'fields': ('rating', 'profit_percentage_per_day', 'roi', 'total_trades', 'followers_count')
        }),
        ('Commission & Status', {
            'fields': ('commission_percentage', 'is_active')
        }),
    )
    
    def has_image(self, obj):
        if obj.profile_image:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    has_image.short_description = 'Profile Image'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self.message_user(request, f'Trader {obj.name} saved successfully!')


@admin.register(CopyTradingSubscription)
class CopyTradingSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'trader', 'amount_invested', 'commission_paid', 
                    'is_active', 'start_date', 'total_earned']
    list_filter = ['is_active', 'start_date']
    search_fields = ['user__username', 'trader__name']
    raw_id_fields = ['user', 'trader']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'user', 'transaction_type', 'amount', 
                    'currency', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'currency', 'created_at']
    search_fields = ['transaction_id', 'user__username', 'user__email', 'blockchain_transaction_id']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at']
    raw_id_fields = ['user']
    
    actions = ['approve_transaction', 'reject_transaction']
    
    def approve_transaction(self, request, queryset):
        for transaction in queryset:
            if transaction.status == 'PENDING':
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
        
        self.message_user(request, f"{queryset.count()} transactions approved")
    approve_transaction.short_description = "Approve selected transactions"
    
    def reject_transaction(self, request, queryset):
        queryset.update(status='REJECTED')
        self.message_user(request, f"{queryset.count()} transactions rejected")
    reject_transaction.short_description = "Reject selected transactions"


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'cryptocurrency', 'amount', 'average_buy_price', 
                    'current_value', 'profit_loss', 'updated_at']
    list_filter = ['cryptocurrency', 'created_at']
    search_fields = ['user__username', 'cryptocurrency']
    raw_id_fields = ['user']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['user', 'trade_type', 'from_currency', 'to_currency', 
                    'from_amount', 'to_amount', 'status', 'created_at']
    list_filter = ['trade_type', 'status', 'created_at']
    search_fields = ['user__username', 'from_currency', 'to_currency']
    raw_id_fields = ['user']


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ['maintenance_mode', 'minimum_deposit', 'minimum_withdrawal', 
                    'trading_fee_percentage', 'withdrawal_fee_percentage', 'updated_at']
    
    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


# ── Investment Plans ──────────────────────────────────────────────────────────

class UserInvestmentInline(admin.TabularInline):
    model = UserInvestment
    extra = 0
    readonly_fields = ['user', 'amount_invested', 'expected_return', 'profit_amount',
                       'status', 'start_date', 'end_date', 'completed_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'roi_percentage', 'duration_days', 'minimum_amount',
                    'maximum_amount_display', 'risk_level', 'subscriber_count',
                    'is_featured', 'is_active', 'created_at']
    list_filter = ['tier', 'risk_level', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'tier', 'description']
    list_editable = ['is_active', 'is_featured']
    inlines = [UserInvestmentInline]

    fieldsets = (
        ('Plan Identity', {
            'fields': ('name', 'tier', 'description', 'risk_level')
        }),
        ('Financial Details', {
            'fields': ('minimum_amount', 'maximum_amount', 'roi_percentage', 'duration_days')
        }),
        ('Features & Visibility', {
            'fields': ('features', 'is_active', 'is_featured')
        }),
    )

    def maximum_amount_display(self, obj):
        if obj.maximum_amount:
            return f'${obj.maximum_amount:,.2f}'
        return format_html('<span style="color:#9ca3af;">Unlimited</span>')
    maximum_amount_display.short_description = 'Max Amount'

    def subscriber_count(self, obj):
        count = obj.subscriptions.count()
        active = obj.subscriptions.filter(status='ACTIVE').count()
        return format_html(
            '<span style="font-weight:600;">{}</span> '
            '<span style="color:#6b7280;font-size:.85em;">({} active)</span>',
            count, active
        )
    subscriber_count.short_description = 'Subscribers'


@admin.register(UserInvestment)
class UserInvestmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'amount_invested', 'expected_return',
                    'profit_amount', 'status', 'start_date', 'end_date', 'days_left']
    list_filter = ['status', 'plan', 'start_date']
    search_fields = ['user__username', 'user__email', 'plan__name']
    readonly_fields = ['user', 'plan', 'amount_invested', 'expected_return',
                       'profit_amount', 'start_date', 'end_date', 'completed_at']
    raw_id_fields = ['user']

    actions = ['mark_completed', 'mark_cancelled']

    def days_left(self, obj):
        if obj.status == 'ACTIVE':
            days = obj.days_remaining
            if days == 0:
                return format_html('<span style="color:#ef4444;font-weight:600;">Due today</span>')
            return format_html('<span style="color:#2563eb;">{} day{}</span>', days, 's' if days != 1 else '')
        elif obj.status == 'COMPLETED':
            return format_html('<span style="color:#16a34a;">✓ Done</span>')
        return format_html('<span style="color:#9ca3af;">—</span>')
    days_left.short_description = 'Days Left'

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for inv in queryset.filter(status='ACTIVE'):
            # Credit principal + profit back to user
            inv.user.account_balance += inv.expected_return
            inv.user.total_profit += inv.profit_amount
            inv.user.save()

            inv.status = 'COMPLETED'
            inv.completed_at = timezone.now()
            inv.save()

            # Record profit transaction
            Transaction.objects.create(
                user=inv.user,
                transaction_type='PROFIT',
                amount=inv.expected_return,
                currency=inv.user.preferred_currency,
                status='COMPLETED',
                description=f'Investment matured: {inv.plan.name} — principal + {inv.plan.roi_percentage}% ROI',
            )
            updated += 1

        self.message_user(
            request,
            f'{updated} investment(s) marked as completed and funds credited to users.'
        )
    mark_completed.short_description = 'Mark selected as completed & credit funds'

    def mark_cancelled(self, request, queryset):
        updated = 0
        for inv in queryset.filter(status='ACTIVE'):
            # Refund principal only
            inv.user.account_balance += inv.amount_invested
            inv.user.save()

            inv.status = 'CANCELLED'
            inv.save()
            updated += 1

        self.message_user(
            request,
            f'{updated} investment(s) cancelled and principal refunded to users.'
        )
    mark_cancelled.short_description = 'Cancel selected & refund principal'


# ============================================
# ENHANCED CHAT ADMIN WITH REPLY FUNCTIONALITY
# ============================================

class AdminReplyForm(forms.ModelForm):
    """Custom form for admin replies"""
    admin_reply = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'cols': 80,
            'placeholder': 'Type your reply to the user here...',
            'style': 'width: 100%; padding: 10px; border: 2px solid #3b82f6; border-radius: 5px;'
        }),
        required=False,
        help_text='Enter your message to send to the user'
    )
    
    class Meta:
        model = SupportChat
        fields = ['status', 'admin_reply']


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ['sender_type', 'sender_name', 'message', 'created_at', 'is_read']
    can_delete = False
    ordering = ['created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SupportChat)
class SupportChatAdmin(admin.ModelAdmin):
    form = AdminReplyForm
    list_display = ['id', 'user', 'status', 'message_count', 'unread_count', 'last_message_preview', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'messages__message']
    readonly_fields = ['created_at', 'updated_at', 'closed_at', 'display_chat_history']
    raw_id_fields = ['user']
    inlines = [SupportMessageInline]
    
    fieldsets = (
        ('Chat Information', {
            'fields': ('user', 'status', 'created_at', 'updated_at', 'closed_at')
        }),
        ('Reply to User', {
            'fields': ('admin_reply',),
            'description': 'Send a message to the user. The user will see your reply in real-time.'
        }),
        ('Chat History', {
            'fields': ('display_chat_history',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['close_chats', 'reopen_chats', 'mark_all_read']
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Total Messages'
    
    def unread_count(self, obj):
        count = obj.messages.filter(is_read=False, sender_type='USER').count()
        if count > 0:
            return format_html('<span style="background-color: #ef4444; color: white; padding: 2px 8px; border-radius: 10px; font-weight: bold;">{}</span>', count)
        return '0'
    unread_count.short_description = 'Unread'
    
    def last_message_preview(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            preview = last_msg.message[:50] + '...' if len(last_msg.message) > 50 else last_msg.message
            color = '#3b82f6' if last_msg.sender_type == 'USER' else '#10b981'
            return format_html('<span style="color: {};">{}: {}</span>', color, last_msg.sender_name, preview)
        return '-'
    last_message_preview.short_description = 'Last Message'
    
    def display_chat_history(self, obj):
        if obj.pk:
            messages = obj.messages.order_by('created_at')
            html = '<div style="background: #f9fafb; padding: 20px; border-radius: 10px; max-height: 500px; overflow-y: auto;">'
            
            for msg in messages:
                bg_color = '#dbeafe' if msg.sender_type == 'USER' else '#d1fae5'
                align = 'left' if msg.sender_type == 'USER' else 'right'
                
                html += f'''
                <div style="margin-bottom: 15px; text-align: {align};">
                    <div style="display: inline-block; max-width: 70%; background: {bg_color}; padding: 10px 15px; border-radius: 10px; text-align: left;">
                        <strong style="color: #1f2937;">{msg.sender_name}</strong>
                        <p style="margin: 5px 0; color: #374151;">{msg.message}</p>
                        <small style="color: #6b7280;">{msg.created_at.strftime("%b %d, %Y %I:%M %p")}</small>
                        {' <span style="color: #10b981;">✓✓</span>' if msg.is_read else ' <span style="color: #9ca3af;">✓</span>'}
                    </div>
                </div>
                '''
            
            html += '</div>'
            return format_html(html)
        return 'Save the chat first to view history'
    
    display_chat_history.short_description = 'Chat Conversation'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        admin_reply = form.cleaned_data.get('admin_reply')
        if admin_reply and admin_reply.strip():
            SupportMessage.objects.create(
                chat=obj,
                sender_type='SUPPORT',
                sender_name=f'{request.user.first_name} {request.user.last_name}' if request.user.first_name else request.user.username,
                message=admin_reply.strip(),
                is_read=False
            )
            
            obj.messages.filter(sender_type='USER', is_read=False).update(is_read=True)
            obj.save()
            
            self.message_user(request, f'Reply sent to {obj.user.username} successfully!', level='success')
    
    def close_chats(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(status='CLOSED', closed_at=timezone.now())
        self.message_user(request, f"{count} chat(s) closed successfully")
    close_chats.short_description = "Close selected chats"
    
    def reopen_chats(self, request, queryset):
        count = queryset.update(status='ACTIVE', closed_at=None)
        self.message_user(request, f"{count} chat(s) reopened successfully")
    reopen_chats.short_description = "Reopen selected chats"
    
    def mark_all_read(self, request, queryset):
        total = 0
        for chat in queryset:
            count = chat.messages.filter(sender_type='USER', is_read=False).update(is_read=True)
            total += count
        self.message_user(request, f"Marked {total} message(s) as read")
    mark_all_read.short_description = "Mark all messages as read"


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'sender_type', 'sender_name', 'message_preview', 'is_read', 'created_at']
    list_filter = ['sender_type', 'is_read', 'created_at']
    search_fields = ['message', 'sender_name', 'chat__user__username']
    readonly_fields = ['chat', 'sender_type', 'sender_name', 'message', 'created_at']
    raw_id_fields = ['chat']
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True