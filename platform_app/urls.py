from django.urls import path
from . import views

urlpatterns = [
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
]