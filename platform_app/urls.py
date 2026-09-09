from django.urls import path
from . import views
from . import admin_views

urlpatterns = [

    # PASSWORD RESET
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('resend-reset-code/', views.resend_reset_code, name='resend_reset_code'),

    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('onboarding/', views.onboarding, name='onboarding'),
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

    # ── Investment Plans ──────────────────────────────────────────────────────
    path('investments/', views.investment_plans, name='investment_plans'),
    path('investments/<int:plan_id>/', views.investment_plan_detail, name='investment_plan_detail'),
    path('investments/my/', views.my_investments, name='my_investments'),

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

    # Products
    path('products/stocks/', views.stocks, name='stocks'),
    path('products/crypto/', views.crypto, name='crypto'),
    path('products/forex/', views.forex, name='forex'),
    path('products/options/', views.options, name='options'),

    # Company
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('careers/', views.careers, name='careers'),
    path('press/', views.press, name='press'),

    # Legal
    path('legal/privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('legal/terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('legal/cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('legal/disclaimer/', views.disclaimer, name='disclaimer'),

    # ── ADMIN ────────────────────────────────────────────────────────────────

    # Dashboard
    path('custom-admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    
    # Users Management
    path('custom-admin/users/', admin_views.admin_users_list, name='admin_users_list'),
    path('custom-admin/users/<int:user_id>/', admin_views.admin_user_detail, name='admin_user_detail'),
    
    # Admins Management
    path('custom-admin/admins/', admin_views.admin_admins_list, name='admin_admins_list'),
    path('custom-admin/admins/promote/', admin_views.admin_promote_user, name='admin_promote_user'),
    path('custom-admin/admins/<int:user_id>/revoke/', admin_views.admin_revoke_admin, name='admin_revoke_admin'),

    # Transactions Management
    path('custom-admin/transactions/', admin_views.admin_transactions_list, name='admin_transactions_list'),
    path('custom-admin/transactions/create/', admin_views.admin_transaction_create, name='admin_transaction_create'),
    path('custom-admin/transactions/<int:transaction_id>/action/', admin_views.admin_transaction_action, name='admin_transaction_action'),
    path('custom-admin/transactions/<int:transaction_id>/delete/', admin_views.admin_transaction_delete, name='admin_transaction_delete'),

    # Copy Traders Management
    path('custom-admin/traders/', admin_views.admin_traders_list, name='admin_traders_list'),
    path('custom-admin/traders/create/', admin_views.admin_trader_create, name='admin_trader_create'),
    path('custom-admin/traders/<int:trader_id>/edit/', admin_views.admin_trader_edit, name='admin_trader_edit'),
    path('custom-admin/traders/<int:trader_id>/delete/', admin_views.admin_trader_delete, name='admin_trader_delete'),

    # Bot Plans Management
    path('custom-admin/bot-plans/', admin_views.admin_bot_plans_list, name='admin_bot_plans_list'),
    path('custom-admin/bot-plans/create/', admin_views.admin_bot_plan_create, name='admin_bot_plan_create'),
    path('custom-admin/bot-plans/<int:plan_id>/edit/', admin_views.admin_bot_plan_edit, name='admin_bot_plan_edit'),
    path('custom-admin/bot-plans/<int:plan_id>/delete/', admin_views.admin_bot_plan_delete, name='admin_bot_plan_delete'),
    path('custom-admin/bot-plans/<int:plan_id>/toggle/', admin_views.admin_bot_plan_toggle, name='admin_bot_plan_toggle'),

    # ── Investment Plans Management ───────────────────────────────────────────
    path('custom-admin/investment-plans/', admin_views.admin_investment_plans_list, name='admin_investment_plans_list'),
    path('custom-admin/investment-plans/create/', admin_views.admin_investment_plan_create, name='admin_investment_plan_create'),
    path('custom-admin/investment-plans/<int:plan_id>/edit/', admin_views.admin_investment_plan_edit, name='admin_investment_plan_edit'),
    path('custom-admin/investment-plans/<int:plan_id>/toggle/', admin_views.admin_investment_plan_toggle, name='admin_investment_plan_toggle'),
    path('custom-admin/investment-plans/<int:plan_id>/delete/', admin_views.admin_investment_plan_delete, name='admin_investment_plan_delete'),

    # Support Chats
    path('custom-admin/support/', admin_views.admin_support_chats, name='admin_support_chats'),
    path('custom-admin/support/<int:chat_id>/', admin_views.admin_chat_detail, name='admin_chat_detail'),
    path('custom-admin/support/<int:chat_id>/close/', admin_views.admin_chat_close, name='admin_chat_close'),
    path('custom-admin/support/<int:chat_id>/delete/', admin_views.admin_chat_delete, name='admin_chat_delete'),

    # User Activities
    path('custom-admin/activities/', admin_views.admin_activities_list, name='admin_activities_list'),

    # Settings
    path('custom-admin/settings/', admin_views.admin_settings, name='admin_settings'),
    path('custom-admin/settings/wallets/<int:wallet_id>/edit/', admin_views.admin_wallet_edit, name='admin_wallet_edit'),
    path('custom-admin/settings/wallets/<int:wallet_id>/delete/', admin_views.admin_wallet_delete, name='admin_wallet_delete'),
    path('custom-admin/settings/wallets/<int:wallet_id>/toggle/', admin_views.admin_wallet_toggle, name='admin_wallet_toggle'),

    # System Logs
    path('custom-admin/logs/', admin_views.admin_system_logs, name='admin_system_logs'),
]