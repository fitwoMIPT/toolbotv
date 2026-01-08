CHOOSE_PLAN_MESSAGE = "Выберите подходящий тариф:"
CHOOSE_PAYMENT_METHOD_MESSAGE = "Выберите удобный способ оплаты:"
VPN_INACTIVE_TEXT = "❌ <b>Статус VPN:</b> Неактивен (срок истек)"
VPN_NO_DATA_TEXT = "ℹ️ <b>Статус VPN:</b> У вас пока нет активных ключей."

def get_profile_text(username, total_spent, total_months, vpn_status_text):
    return (
        f"👤 <b>Профиль:</b> {username}\n\n"
        f"💰 <b>Потрачено всего:</b> {total_spent:.0f} RUB\n"
        f"📅 <b>Приобретено месяцев:</b> {total_months}\n\n"
        f"{vpn_status_text}"
    )

def get_vpn_active_text(days_left, hours_left):
    return (
        f"✅ <b>Статус VPN:</b> Активен\n"
        f"⏳ <b>Осталось:</b> {days_left} д. {hours_left} ч."
    )

def get_key_info_text(key_number, expiry_date, created_date, connection_string):
    expiry_formatted = expiry_date.strftime('%d.%m.%Y в %H:%M')
    created_formatted = created_date.strftime('%d.%m.%Y в %H:%M')
    
    return (
        f"<b>🔑 Информация о ключе #{key_number}</b>\n\n"
        f"<b>➕ Приобретён:</b> {created_formatted}\n"
        f"<b>⏳ Действителен до:</b> {expiry_formatted}\n\n"
        f"<code>{connection_string}</code>"
    )

def get_purchase_success_text(action: str, key_number: int, expiry_date, connection_string: str):
    action_text = "обновлен" if action == "extend" else "готов"
    expiry_formatted = expiry_date.strftime('%d.%m.%Y в %H:%M')

    return (
        f"🎉 <b>Ваш ключ #{key_number} {action_text}!</b>\n\n"
        f"⏳ <b>Он будет действовать до:</b> {expiry_formatted}\n\n"
        f"<code>{connection_string}</code>"
    )

from cryptography.fernet import Fernet
import base64
import logging

logger = logging.getLogger(__name__)

def encrypt_user_id(user_id: int, key: str) -> str:
    f = Fernet(key.encode())
    encrypted = f.encrypt(str(user_id).encode()).decode()
    # Remove Base64 padding (=) for cleaner URL
    return encrypted.rstrip('=')

def decrypt_user_id(encrypted: str, key: str) -> int | None:
    try:
        # Fernet uses URL-safe Base64 which always ends with = or == for padding
        # Since we strip = during encryption, we need to add it back for decryption
        # Calculate how many = chars are needed (0, 1, or 2)
        padding_needed = (4 - len(encrypted) % 4) % 4
        padded = encrypted + ('=' * padding_needed)
        f = Fernet(key.encode())
        decrypted = f.decrypt(padded.encode()).decode()
        return int(decrypted)
    except Exception as e:
        logger.warning(f"Failed to decrypt referral code '{encrypted}': {e}")
        return None