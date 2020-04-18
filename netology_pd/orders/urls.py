from django.urls import path
from rest_framework import renderers

from orders.views import (CategoriesView, CartView, ConfirmAccountView,
                          ContactView, LoadInfo, LoginView, OrderView,
                          OrdersView, RegisterView, PasswordConfirmView,
                          PasswordResetView, ProductInfoView, ProductsView,
                          ShopOrders, ShopsView, StateChange, UserView)

shops_list = ShopsView.as_view({'get': 'list'})
categories_list = CategoriesView.as_view({'get': 'list'})

app_name = 'orders'
urlpatterns = [
    path('partner/loadinfo', LoadInfo.as_view(), name='partner-update'),
    path('partner/state', StateChange.as_view(), name='partner-state'),
    path('partner/orders', ShopOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccountView.as_view(),
         name='user-register-confirm'),
    path('user/details', UserView.as_view(), name='user-details'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    path('user/login', LoginView.as_view(), name='user-login'),
    path('user/password_reset', PasswordResetView.as_view(),
         name='password-reset'),
    path('user/password_reset/confirm', PasswordConfirmView.as_view(),
         name='password-reset-confirm'),
    path('categories', categories_list, name='categories'),
    path('shops', shops_list, name='shops'),
    path('products', ProductsView.as_view(), name='products'),
    path('product_info/<int:product_id>/', ProductInfoView.as_view(),
         name='product_info'),
    path('cart', CartView.as_view(), name='cart'),
    path('order', OrderView.as_view(), name='order'),
    path('orders', OrdersView.as_view(), name='orders'),

]
