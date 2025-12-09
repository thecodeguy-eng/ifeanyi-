from django.urls import path
from . import views
from . import admin_views

urlpatterns = [

    # PASSWORD RESET - ADD THESE NEW PATHS
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('resend-reset-code/', views.resend_reset_code, name='resend_reset_code'),


    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Portfolio
    path('portfolio/', views.portfolio, name='portfolio'),
    
    # Trading
    path('trading/', views.trading, name='trading'),
    
    # Trading Bot
    path('trading-bot/', views.trading_bot, name='trading_bot'),
    path('trading-bot/purchase/<int:plan_id>/', views.purchase_bot, name='purchase_bot'),
    
    # Copy Trading
    path('copy-trading/', views.copy_trading, name='copy_trading'),
    path('copy-trading/<int:trader_id>/', views.copy_trader_detail, name='copy_trader_detail'),
    
    # Deposit & Withdrawal
    path('deposit/', views.deposit, name='deposit'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
    path('payment/', views.payment_page, name='payment_page'),
    
    # Transactions
    path('transactions/', views.transactions, name='transactions'),
    
    # API
    path('api/crypto-prices/', views.get_crypto_prices, name='get_crypto_prices'),

    # Support Chat
    path('chat/get-or-create/', views.get_or_create_active_chat, name='get_or_create_chat'),
    path('chat/send-message/', views.send_support_message, name='send_support_message'),
    path('chat/get-messages/', views.get_chat_messages, name='get_chat_messages'),
    path('chat/clear/', views.clear_support_chat, name='clear_support_chat'),



    # ADMIN_URL
    
    # Dashboard
    path('custom-admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    
    # Users Management
    path('custom-admin/users/', admin_views.admin_users_list, name='admin_users_list'),
    path('custom-admin/users/<int:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    
    # Transactions Management
    path('custom-admin/transactions/', admin_views.admin_transactions_list, name='admin_transactions_list'),
    path('custom-admin/transactions/<int:transaction_id>/action/', admin_views.admin_transaction_action, name='admin_transaction_action'),
    
    # Copy Traders Management
    path('custom-admin/traders/', admin_views.admin_traders_list, name='admin_traders_list'),
    path('custom-admin/traders/create/', admin_views.admin_trader_create, name='admin_trader_create'),
    path('custom-admin/traders/<int:trader_id>/edit/', admin_views.admin_trader_edit, name='admin_trader_edit'),
    path('custom-admin/traders/<int:trader_id>/delete/', admin_views.admin_trader_delete, name='admin_trader_delete'),
    
    # Bot Plans Management
    path('custom-admin/bot-plans/', admin_views.admin_bot_plans_list, name='admin_bot_plans_list'),
    
    # Support Chats
    path('custom-admin/support/', admin_views.admin_support_chats, name='admin_support_chats'),
    path('custom-admin/support/<int:chat_id>/', admin_views.admin_chat_detail, name='admin_chat_detail'),
    
    # User Activities
    path('custom-admin/activities/', admin_views.admin_activities_list, name='admin_activities_list'),
    
    # Settings
    path('custom-admin/settings/', admin_views.admin_settings, name='admin_settings'),
    
    # System Logs
    path('custom-admin/logs/', admin_views.admin_system_logs, name='admin_system_logs'),
]