# handlers/system/__init__.py
"""
Системные обработчики
"""

from .errors import error_handler
from .utils import (
    utils_callbacks_router, handle_utils_callback,
    handle_back_to_menu_callback, handle_support_callback, 
    handle_faq_callback, handle_user_guide_callback,
    handle_payment_history_callback, cancel
)
from .referrals import (
    referrals_callbacks_router, handle_referrals_callback,
    handle_referrals_menu_callback, handle_referral_info_callback,
    handle_copy_referral_link_callback, handle_my_referrals_callback
)
from .payment_checker import (
    check_payment_status_and_update_message, handle_successful_payment_message,
    handle_expired_payment_message
)

__all__ = [
    # Errors
    'error_handler',
    
    # Utils
    'utils_callbacks_router', 'handle_utils_callback',
    'handle_back_to_menu_callback', 'handle_support_callback',
    'handle_faq_callback', 'handle_user_guide_callback',
    'handle_payment_history_callback', 'cancel',
    
    # Referrals
    'referrals_callbacks_router', 'handle_referrals_callback',
    'handle_referrals_menu_callback', 'handle_referral_info_callback',
    'handle_copy_referral_link_callback', 'handle_my_referrals_callback',
    
    # Payment Checker
    'check_payment_status_and_update_message', 'handle_successful_payment_message',
    'handle_expired_payment_message'
]