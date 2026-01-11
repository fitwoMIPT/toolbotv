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
    import base64
    data = str(user_id).encode()
    key_bytes = key.encode() * (len(data) // len(key.encode()) + 1)
    key_bytes = key_bytes[:len(data)]
    encrypted = bytes(a ^ b for a, b in zip(data, key_bytes))
    return base64.b64encode(encrypted).decode().rstrip('=')

def decrypt_user_id(encrypted: str, key: str) -> int | None:
    try:
        import base64
        # Add back padding
        padding_needed = (4 - len(encrypted) % 4) % 4
        padded = encrypted + ('=' * padding_needed)
        encrypted_bytes = base64.b64decode(padded)
        key_bytes = key.encode() * (len(encrypted_bytes) // len(key.encode()) + 1)
        key_bytes = key_bytes[:len(encrypted_bytes)]
        decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key_bytes))
        return int(decrypted.decode())
    except Exception as e:
        logger.warning(f"Failed to decrypt referral code '{encrypted}': {e}")
        return None