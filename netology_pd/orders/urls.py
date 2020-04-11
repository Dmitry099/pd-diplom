from django.urls import path
# from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from orders.views import LoadInfo, RegisterView, LoginView, ConfirmAccountView, ProductsView, ShopsView, ProductInfoView

# PartnerUpdate, RegisterAccount, LoginAccount, CategoryView, ShopView, ProductInfoView, \
#     BasketView, \
#     AccountDetails, ContactView, OrderView, PartnerState, PartnerOrders, ConfirmAccount

app_name = 'backend'
urlpatterns = [
    path('partner/loadinfo', LoadInfo.as_view(), name='partner-update'),
    # path('partner/state', PartnerState.as_view(), name='partner-state'),
    # path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterView.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccountView.as_view(), name='user-register-confirm'),
    # path('user/details', AccountDetails.as_view(), name='user-details'),
    # path('user/contact', ContactView.as_view(), name='user-contact'),
    path('user/login', LoginView.as_view(), name='user-login'),
    # path('user/password_reset', reset_password_request_token, name='password-reset'),
    # path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    # path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopsView.as_view(), name='shops'),
    path('products', ProductsView.as_view(), name='products'),
    path('product_info/<int:product_id>/', ProductInfoView.as_view(), name='product_info'),
    # path('basket', BasketView.as_view(), name='basket'),
    # path('order', OrderView.as_view(), name='order'),

]
