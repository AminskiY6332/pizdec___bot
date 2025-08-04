from .user.commands import start, menu, help_command, check_training, check_user_blocked, extract_utm_from_text
from .user.messages import handle_text, handle_email_input, handle_email_change_input, handle_photo, handle_admin_text
from .commands import debug_avatars
from .user.callbacks import handle_user_callback
from .user.generation import (
    generation_router, generate_photo_for_user, handle_admin_style_selection,
    handle_admin_custom_prompt, handle_admin_aspect_ratio_selection,
    handle_admin_generation_result, process_image_generation, start_admin_generation,
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
    check_resources, check_active_avatar, check_style_config, create_payment_link
)
from .admin_panel import show_admin_stats
from .user_management import show_user_actions, show_user_profile_admin, show_user_avatars_admin, delete_user_admin
from .broadcast import broadcast_message_admin
from .visualization import handle_activity_dates_input
from .photo_transform import photo_transform_router, init_photo_generator


__all__ = [
    'start', 'menu', 'help_command', 'check_training', 'check_user_blocked', 'extract_utm_from_text',
    'handle_text', 'handle_email_input', 'handle_email_change_input', 'handle_photo',
    'handle_admin_text', 'delete_user_admin',
    'error_handler',
    'safe_escape_markdown', 'send_message_with_fallback',  
    'safe_answer_callback', 'delete_message_safe', 'check_user_permissions',
    'get_user_display_name', 'format_user_mention', 'truncate_text',
    'send_typing_action', 'send_upload_photo_action', 'send_upload_video_action',
    'get_tariff_text', 'check_resources', 'check_active_avatar',
    'check_style_config', 'create_payment_link',
    'show_admin_stats', 'show_user_actions', 'show_user_profile_admin',
    'show_user_avatars_admin', 'broadcast_message_admin',
    'handle_activity_dates_input',
    'photo_transform_router',
    'init_photo_generator',
    'generation_router', 'generate_photo_for_user', 'handle_admin_style_selection',
    'handle_admin_custom_prompt', 'handle_admin_aspect_ratio_selection',
    'handle_admin_generation_result', 'process_image_generation', 'start_admin_generation',
    'generation_cancel', 'generation_callback_handler', 'handle_admin_prompt_message',
    'check_payment_status_and_update_message', 'handle_successful_payment_message',
    'handle_expired_payment_message', 'schedule_payment_check'
]