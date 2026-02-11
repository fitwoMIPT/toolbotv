import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery, Update
from aiogram.enums import ChatMemberStatus
from shop_bot.data_manager.database import get_user, get_setting

logger = logging.getLogger(__name__)


def _extract_event(event: TelegramObject):
    """Извлекает Message или CallbackQuery из Update (dp.update middleware получает Update, а не Message/CallbackQuery)."""
    if isinstance(event, Update):
        if event.callback_query:
            return event.callback_query
        if event.message:
            return event.message
    return event


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
            inner = _extract_event(event)
            if isinstance(inner, CallbackQuery):
                await inner.answer(ban_message_text, show_alert=True)
            elif isinstance(inner, Message):
                await inner.answer(ban_message_text)
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
        
        inner = _extract_event(event)
        logger.debug(f"SubCheck: user={user.id}, event_type={type(event).__name__}, inner_type={type(inner).__name__}")
        
        # Пропускаем проверку для команды /start и онбординга
        if isinstance(inner, Message) and inner.text and inner.text.startswith('/start'):
            logger.debug(f"SubCheck: skipping /start for user {user.id}")
            return await handler(event, data)
        if isinstance(inner, CallbackQuery) and inner.data == "check_subscription_and_agree":
            logger.debug(f"SubCheck: skipping onboarding callback for user {user.id}")
            return await handler(event, data)
        
        is_subscription_forced = get_setting("force_subscription") == "true"
        if not is_subscription_forced:
            logger.debug(f"SubCheck: force_subscription is off, passing through")
            return await handler(event, data)
        
        channel_url = get_setting("channel_url")
        if not channel_url:
            logger.debug(f"SubCheck: no channel_url configured, passing through")
            return await handler(event, data)
        
        # Проверяем только зарегистрированных пользователей
        user_data = get_user(user.id)
        if not user_data or not user_data.get('agreed_to_terms'):
            logger.debug(f"SubCheck: user {user.id} not registered or not agreed, passing through")
            return await handler(event, data)
        
        try:
            bot: Bot = data.get('bot')
            if not bot:
                logger.debug(f"SubCheck: no bot instance, passing through")
                return await handler(event, data)
            
            if '@' not in channel_url and 't.me/' not in channel_url:
                logger.info(f"SubCheck: invalid channel_url format: '{channel_url}', passing through")
                return await handler(event, data)
            
            channel_id = '@' + channel_url.split('/')[-1] if 't.me/' in channel_url else channel_url
            logger.info(f"SubCheck: checking user {user.id} membership in {channel_id}")
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user.id)
            logger.info(f"SubCheck: user {user.id} status = {member.status}")
            
            if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                return await handler(event, data)
            else:
                # Для CallbackQuery используем короткий текст (лимит 200 символов)
                if isinstance(inner, CallbackQuery):
                    await inner.answer(
                        "⚠️ Подпишитесь на канал для использования бота!",
                        show_alert=True
                    )
                elif isinstance(inner, Message):
                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                    kb = InlineKeyboardBuilder()
                    kb.button(text="📢 Перейти в канал", url=channel_url)
                    kb.adjust(1)
                    await inner.answer(
                        "⚠️ <b>Для использования бота необходимо быть подписанным на канал.</b>\n\n"
                        "Подпишитесь и попробуйте снова.",
                        reply_markup=kb.as_markup()
                    )
                else:
                    logger.warning(f"SubCheck: unknown inner type {type(inner).__name__}, can't respond")
                return
                
        except Exception as e:
            logger.warning(f"SubCheck: subscription check failed for user {user.id}: {e}", exc_info=True)
            # Если проверка не удалась — пропускаем, чтобы не блокировать пользователя
            return await handler(event, data)
