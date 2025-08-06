from .user.commands import start, menu, help_command, check_training, check_user_blocked, extract_utm_from_text
from .user.messages import handle_text, handle_email_input, handle_email_change_input, handle_photo, handle_admin_text, handle_video
from .admin.commands import debug_avatars
from .user.callbacks import handle_user_callback
from .admin.generation import (
    generation_router, generate_photo_for_user, handle_admin_style_selection,
    handle_admin_custom_prompt, handle_admin_aspect_ratio_selection,
    handle_admin_generation_result, process_image_generation,
    cancel as generation_cancel, generation_callback_handler, handle_admin_prompt_message
)
from .user.payments import (
    check_payment_status_and_update_message, handle_successful_payment_message,
    handle_expired_payment_message, schedule_payment_check
)
from .system.errors import error_handler
from .utils import (
    safe_escape_markdown, send_message_with_fallback, safe_answer_callback,
    delete_message_safe, check_user_permissions, get_user_display_name,
    format_user_mention, truncate_text, send_typing_action,
    send_upload_photo_action, send_upload_video_action, get_tariff_text,
    check_resources, check_active_avatar, check_style_config, create_payment_link,
    get_bot_summary_stats
)

from .admin.user_management import show_user_actions, show_user_profile_admin, show_user_avatars_admin, delete_user_admin
from .admin.broadcast import broadcast_message_admin
from .admin.panels import (
    admin_panel, show_admin_stats,
    get_all_failed_avatars, delete_all_failed_avatars, admin_show_failed_avatars,
    admin_confirm_delete_all_failed, admin_execute_delete_all_failed,
    send_daily_payments_report, cancel as panels_cancel
)
from .admin.broadcast import (
    broadcast_router, initiate_broadcast, clear_user_data
)
from .admin.callbacks import (
    admin_callbacks_router, show_dev_test_payment,
    handle_admin_send_generation, handle_admin_regenerate
)
from .admin.visualization import (
    visualization_router, show_visualization, visualize_payments,
    visualize_registrations, visualize_generations, show_activity_stats,
    handle_activity_stats, handle_activity_dates_input, cancel as visualization_cancel,
    visualization_callback_handler
)
from .user.photo_transform import photo_transform_router, init_photo_generator


__all__ = [
    'start', 'menu', 'help_command', 'check_training', 'check_user_blocked', 'extract_utm_from_text',
    'handle_text', 'handle_email_input', 'handle_email_change_input', 'handle_photo',
    'handle_admin_text', 'handle_video', 'delete_user_admin',
    'error_handler',
    'safe_escape_markdown', 'send_message_with_fallback',  
    'safe_answer_callback', 'delete_message_safe', 'check_user_permissions',
    'get_user_display_name', 'format_user_mention', 'truncate_text',
    'send_typing_action', 'send_upload_photo_action', 'send_upload_video_action',
    'get_tariff_text', 'check_resources', 'check_active_avatar',
    'check_style_config', 'create_payment_link', 'get_bot_summary_stats',
               'admin_panel', 'show_admin_stats',
           'get_all_failed_avatars', 'delete_all_failed_avatars', 'admin_show_failed_avatars',
           'admin_confirm_delete_all_failed', 'admin_execute_delete_all_failed',
           'send_daily_payments_report', 'panels_cancel',
           'broadcast_router', 'initiate_broadcast', 'clear_user_data',
           'admin_callbacks_router', 'show_dev_test_payment',
           'handle_admin_send_generation', 'handle_admin_regenerate',
           'show_user_actions', 'show_user_profile_admin',
           'show_user_avatars_admin', 'broadcast_message_admin',
               'visualization_router', 'show_visualization', 'visualize_payments',
           'visualize_registrations', 'visualize_generations', 'show_activity_stats',
           'handle_activity_stats', 'handle_activity_dates_input', 'visualization_cancel',
           'visualization_callback_handler',
    'photo_transform_router',
    'init_photo_generator',
               'generation_router', 'generate_photo_for_user', 'handle_admin_style_selection',
           'handle_admin_custom_prompt', 'handle_admin_aspect_ratio_selection',
           'handle_admin_generation_result', 'process_image_generation',
           'generation_cancel', 'generation_callback_handler', 'handle_admin_prompt_message',
    'check_payment_status_and_update_message', 'handle_successful_payment_message',
    'handle_expired_payment_message', 'schedule_payment_check'
]
