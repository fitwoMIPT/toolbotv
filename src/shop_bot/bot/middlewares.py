import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, Chat
from aiogram.enums import ChatMemberStatus
from shop_bot.data_manager.database import get_user, get_setting

logger = logging.getLogger(__name__)

class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if not user:
            return await handler(event, data)

        user_data = get_user(user.id)
        if user_data and user_data.get('is_banned'):
            ban_message_text = "Вы заблокированы и не можете использовать этого бота."
            if isinstance(event, CallbackQuery):
                await event.answer(ban_message_text, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(ban_message_text)
            return
        
        return await handler(event, data)


class SubscriptionCheckMiddleware(BaseMiddleware):
    """Проверяет подписку на канал при каждом действии (если включена force_subscription)."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get('event_from_user')
        if not user:
            return await handler(event, data)
        
        # Пропускаем проверку для команды /start и онбординга
        if isinstance(event, Message) and event.text and event.text.startswith('/start'):
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == "check_subscription_and_agree":
            return await handler(event, data)
        
        is_subscription_forced = get_setting("force_subscription") == "true"
        if not is_subscription_forced:
            return await handler(event, data)
        
        channel_url = get_setting("channel_url")
        if not channel_url:
            return await handler(event, data)
        
        # Проверяем только зарегистрированных пользователей
        user_data = get_user(user.id)
        if not user_data or not user_data.get('agreed_to_terms'):
            return await handler(event, data)
        
        try:
            bot: Bot = data.get('bot')
            if not bot:
                return await handler(event, data)
            
            if '@' not in channel_url and 't.me/' not in channel_url:
                return await handler(event, data)
            
            channel_id = '@' + channel_url.split('/')[-1] if 't.me/' in channel_url else channel_url
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user.id)
            
            if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                return await handler(event, data)
            else:
                unsub_text = (
                    "⚠️ Для использования бота необходимо быть подписанным на канал.\n"
                    f"📢 Подпишитесь: {channel_url}\n\n"
                    "После подписки попробуйте снова."
                )
                if isinstance(event, CallbackQuery):
                    await event.answer(unsub_text, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(unsub_text)
                return
                
        except Exception as e:
            logger.warning(f"Subscription check failed for user {user.id}: {e}")
            # Если проверка не удалась — пропускаем, чтобы не блокировать пользователя
            return await handler(event, data)
