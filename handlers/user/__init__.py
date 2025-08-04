# handlers/user/__init__.py
"""
Пользовательские обработчики
"""

from .onboarding import (
    onboarding_router, send_onboarding_message, schedule_welcome_message,
    schedule_daily_reminders, send_daily_reminders, proceed_to_tariff_callback,
    setup_onboarding_handlers
)
from .commands import (
    start, menu, help_command, check_training, 
    check_user_blocked, extract_utm_from_text
)
from .messages import (
    handle_text, handle_email_input, handle_email_change_input,
    handle_manual_prompt_input, handle_llama_prompt_input,
    handle_custom_prompt_photo_input, handle_admin_text,
    handle_admin_chat_message, handle_photo, handle_prompt_based_photo,
    handle_photo_to_photo_reference, handle_photo_to_photo_mask
)
from .callbacks import (
    handle_proceed_to_payment_callback, handle_user_callback, handle_back_to_menu_callback,
    delete_all_videos, handle_photo_generate_menu_callback, handle_video_generate_menu_callback,
    handle_generate_with_avatar_callback, handle_style_selection_callback, handle_style_choice_callback,
    handle_male_styles_page_callback, handle_female_styles_page_callback, handle_photo_to_photo_callback,
    handle_ai_video_callback, handle_video_style_choice_callback, handle_custom_prompt_manual_callback,
    handle_custom_prompt_llama_callback, handle_confirm_video_generation_callback, handle_confirm_assisted_prompt_callback,
    handle_edit_assisted_prompt_callback, handle_skip_prompt_callback, handle_aspect_ratio_callback,
    handle_back_to_aspect_selection_callback, handle_back_to_style_selection_callback, handle_confirm_generation_callback,
    handle_rating_callback, handle_user_profile_callback, handle_check_subscription_callback,
    handle_user_stats_callback, handle_subscribe_callback, handle_payment_callback, handle_my_avatars_callback,
    handle_select_avatar_callback, handle_train_flux_callback, handle_continue_upload_callback,
    handle_start_training_callback, handle_support_callback, handle_help_callback, handle_terms_callback,
    handle_select_new_male_avatar_styles_callback, handle_select_new_female_avatar_styles_callback,
    handle_confirm_start_training_callback, handle_back_to_avatar_name_input_callback, handle_use_suggested_trigger_callback,
    handle_confirm_photo_quality_callback, handle_repeat_last_generation_callback, handle_change_email_callback,
    handle_confirm_change_email_callback, handle_skip_mask_callback, ask_for_aspect_ratio_callback, cancel
)
from .generation import (
    generation_router, generate_photo_for_user, handle_admin_style_selection,
    handle_admin_custom_prompt, handle_admin_aspect_ratio_selection,
    handle_admin_generation_result, process_image_generation, start_admin_generation,
    cancel as generation_cancel, generation_callback_handler, handle_admin_prompt_message
)
from .payments import (
    check_payment_status_and_update_message, handle_successful_payment_message,
    handle_expired_payment_message, schedule_payment_check
)

__all__ = [
    # Onboarding
    'onboarding_router', 'send_onboarding_message', 'schedule_welcome_message',
    'schedule_daily_reminders', 'send_daily_reminders', 'proceed_to_tariff_callback',
    'setup_onboarding_handlers',
    
    # Commands
    'start', 'menu', 'help_command', 'check_training',
    'check_user_blocked', 'extract_utm_from_text',
    
    # Messages
    'handle_text', 'handle_email_input', 'handle_email_change_input',
    'handle_manual_prompt_input', 'handle_llama_prompt_input',
    'handle_custom_prompt_photo_input', 'handle_admin_text',
    'handle_admin_chat_message', 'handle_photo', 'handle_prompt_based_photo',
    'handle_photo_to_photo_reference', 'handle_photo_to_photo_mask',
    
    # Callbacks
    'handle_proceed_to_payment_callback', 'handle_user_callback', 'handle_back_to_menu_callback',
    'delete_all_videos', 'handle_photo_generate_menu_callback', 'handle_video_generate_menu_callback',
    'handle_generate_with_avatar_callback', 'handle_style_selection_callback', 'handle_style_choice_callback',
    'handle_male_styles_page_callback', 'handle_female_styles_page_callback', 'handle_photo_to_photo_callback',
    'handle_ai_video_callback', 'handle_video_style_choice_callback', 'handle_custom_prompt_manual_callback',
    'handle_custom_prompt_llama_callback', 'handle_confirm_video_generation_callback', 'handle_confirm_assisted_prompt_callback',
    'handle_edit_assisted_prompt_callback', 'handle_skip_prompt_callback', 'handle_aspect_ratio_callback',
    'handle_back_to_aspect_selection_callback', 'handle_back_to_style_selection_callback', 'handle_confirm_generation_callback',
    'handle_rating_callback', 'handle_user_profile_callback', 'handle_check_subscription_callback',
    'handle_user_stats_callback', 'handle_subscribe_callback', 'handle_payment_callback', 'handle_my_avatars_callback',
    'handle_select_avatar_callback', 'handle_train_flux_callback', 'handle_continue_upload_callback',
    'handle_start_training_callback', 'handle_support_callback', 'handle_help_callback', 'handle_terms_callback',
    'handle_select_new_male_avatar_styles_callback', 'handle_select_new_female_avatar_styles_callback',
    'handle_confirm_start_training_callback', 'handle_back_to_avatar_name_input_callback', 'handle_use_suggested_trigger_callback',
    'handle_confirm_photo_quality_callback', 'handle_repeat_last_generation_callback', 'handle_change_email_callback',
    'handle_confirm_change_email_callback', 'handle_skip_mask_callback', 'ask_for_aspect_ratio_callback', 'cancel',
    
    # Generation
    'generation_router', 'generate_photo_for_user', 'handle_admin_style_selection',
    'handle_admin_custom_prompt', 'handle_admin_aspect_ratio_selection',
    'handle_admin_generation_result', 'process_image_generation', 'start_admin_generation',
    'generation_cancel', 'generation_callback_handler', 'handle_admin_prompt_message',
    
    # Payments
    'check_payment_status_and_update_message', 'handle_successful_payment_message',
    'handle_expired_payment_message', 'schedule_payment_check',
    
    # TODO: Добавить остальные user модули при переносе
]