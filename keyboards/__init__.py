# keyboards/__init__.py
"""
Модуль клавиатур для Telegram бота
Содержит все инлайн-клавиатуры, организованные по функциональности
"""

from .base import (
    create_back_keyboard,
    create_confirmation_keyboard,
    create_error_keyboard
)

from .main_menu import (
    create_main_menu_keyboard,
    create_photo_generate_menu_keyboard,
    create_video_generate_menu_keyboard
)

from .generation import (
    create_style_selection_keyboard,
    create_aspect_ratio_keyboard,
    create_avatar_style_choice_keyboard,
    create_new_male_avatar_styles_keyboard,
    create_new_female_avatar_styles_keyboard,
    create_video_styles_keyboard,
    create_prompt_selection_keyboard,
    create_generation_in_progress_keyboard
)

from .user_profile import (
    create_user_profile_keyboard,
    create_avatar_selection_keyboard,
    create_training_keyboard,
    create_rating_keyboard,
    create_payment_success_keyboard
)

from .admin import (
    create_admin_keyboard,
    create_admin_user_actions_keyboard
)

from .payments import (
    create_subscription_keyboard,
    create_payment_only_keyboard
)

from .support import (
    create_faq_keyboard,
    create_support_keyboard,
    create_referral_keyboard
)

from .broadcast import (
    create_broadcast_keyboard,
    create_broadcast_with_payment_audience_keyboard,
    create_dynamic_broadcast_keyboard
)

from .utils import (
    create_photo_upload_keyboard,
    create_video_status_keyboard,
    send_avatar_training_message
)

# Экспорт всех клавиатур для обратной совместимости
__all__ = [
    # Base keyboards
    'create_back_keyboard',
    'create_confirmation_keyboard', 
    'create_error_keyboard',
    
    # Main menu keyboards
    'create_main_menu_keyboard',
    'create_photo_generate_menu_keyboard',
    'create_video_generate_menu_keyboard',
    
    # Generation keyboards
    'create_style_selection_keyboard',
    'create_aspect_ratio_keyboard',
    'create_avatar_style_choice_keyboard',
    'create_new_male_avatar_styles_keyboard',
    'create_new_female_avatar_styles_keyboard',
    'create_video_styles_keyboard',
    'create_prompt_selection_keyboard',
    'create_generation_in_progress_keyboard',
    
    # User profile keyboards
    'create_user_profile_keyboard',
    'create_avatar_selection_keyboard',
    'create_training_keyboard',
    'create_rating_keyboard',
    'create_payment_success_keyboard',
    
    # Admin keyboards
    'create_admin_keyboard',
    'create_admin_user_actions_keyboard',
    
    # Payment keyboards
    'create_subscription_keyboard',
    'create_payment_only_keyboard',
    
    # Support keyboards
    'create_faq_keyboard',
    'create_support_keyboard',
    'create_referral_keyboard',
    
    # Broadcast keyboards
    'create_broadcast_keyboard',
    'create_broadcast_with_payment_audience_keyboard',
    'create_dynamic_broadcast_keyboard',
    
    # Utility keyboards
    'create_photo_upload_keyboard',
    'create_video_status_keyboard',
    'send_avatar_training_message'
] 