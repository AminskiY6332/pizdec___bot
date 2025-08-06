# handlers/admin/__init__.py
"""
Административные обработчики
"""

from .commands import (
    dev_test_tariff, debug_avatars, addcook, delcook, 
    addnew, delnew, user_id_info,
    confirm_addcook_callback, confirm_delcook_callback,
    confirm_addnew_callback, confirm_delnew_callback,
    cancel_admin_operation_callback
)
from .user_management import (
    show_user_actions, show_user_profile_admin, show_user_avatars_admin,
    show_user_logs, change_balance_admin, handle_balance_change_input,
    delete_user_admin, confirm_delete_user, block_user_admin,
    confirm_block_user, search_users_admin, handle_user_search_input,
    confirm_reset_avatar, cancel, handle_block_reason_input,
    user_management_callback_handler
)
from .payments import (
    show_payments_menu, handle_payments_date, handle_manual_date_input,
    handle_payments_date_input, show_replicate_costs, cancel_payments,
    payments_callback_handler, handle_payments_date_input_wrapper,
    cancel_payments_wrapper, payments_router
)
from .generation import (
    generation_router, generate_photo_for_user, handle_admin_style_selection,
    handle_admin_custom_prompt, handle_admin_aspect_ratio_selection,
    handle_admin_generation_result, process_image_generation, cancel as generation_cancel,
    generation_callback_handler, handle_admin_prompt_message
)
from .visualization import (
    visualization_router, show_visualization, visualize_payments,
    visualize_registrations, visualize_generations, show_activity_stats,
    handle_activity_stats, handle_activity_dates_input, cancel as visualization_cancel,
    visualization_callback_handler
)
from .panels import (
    admin_panel, show_admin_stats,
    get_all_failed_avatars, delete_all_failed_avatars, admin_show_failed_avatars,
    admin_confirm_delete_all_failed, admin_execute_delete_all_failed,
    send_daily_payments_report, cancel as panels_cancel
)
from .broadcast import (
    broadcast_router, initiate_broadcast, clear_user_data
)
from .callbacks import (
    admin_callbacks_router, show_dev_test_payment,
    handle_admin_send_generation, handle_admin_regenerate
)

__all__ = [
    # Commands
    'dev_test_tariff', 'debug_avatars', 'addcook', 'delcook', 
    'addnew', 'delnew', 'user_id_info',
    'confirm_addcook_callback', 'confirm_delcook_callback',
    'confirm_addnew_callback', 'confirm_delnew_callback',
    'cancel_admin_operation_callback',
    
    # User Management
    'show_user_actions', 'show_user_profile_admin', 'show_user_avatars_admin',
    'show_user_logs', 'change_balance_admin', 'handle_balance_change_input',
    'delete_user_admin', 'confirm_delete_user', 'block_user_admin',
    'confirm_block_user', 'search_users_admin', 'handle_user_search_input',
    'confirm_reset_avatar', 'cancel', 'handle_block_reason_input',
    'user_management_callback_handler',
    
    # Payments
    'show_payments_menu', 'handle_payments_date', 'handle_manual_date_input',
    'handle_payments_date_input', 'show_replicate_costs', 'cancel_payments',
    'payments_callback_handler', 'handle_payments_date_input_wrapper',
    'cancel_payments_wrapper', 'payments_router',
    
    # Generation
    'generation_router', 'generate_photo_for_user', 'handle_admin_style_selection',
    'handle_admin_custom_prompt', 'handle_admin_aspect_ratio_selection',
    'handle_admin_generation_result', 'process_image_generation', 'generation_cancel',
    'generation_callback_handler', 'handle_admin_prompt_message',
    
    # Visualization
    'visualization_router', 'show_visualization', 'visualize_payments',
    'visualize_registrations', 'visualize_generations', 'show_activity_stats',
    'handle_activity_stats', 'handle_activity_dates_input', 'visualization_cancel',
    'visualization_callback_handler',
    
    # Panels
    'admin_panel', 'show_admin_stats',
    'get_all_failed_avatars', 'delete_all_failed_avatars', 'admin_show_failed_avatars',
    'admin_confirm_delete_all_failed', 'admin_execute_delete_all_failed',
    'send_daily_payments_report', 'panels_cancel',
    
    # Broadcast
    'broadcast_router', 'initiate_broadcast', 'clear_user_data',
    
    # Callbacks
    'admin_callbacks_router', 'show_dev_test_payment',
    'handle_admin_send_generation', 'handle_admin_regenerate',
    
    # TODO: Добавить остальные модули по мере переноса
]