# Разовый вход в Telegram. Запусти в Google Colab (colab.research.google.com):
# первая ячейка:   !pip install -q telethon
# вторая ячейка:   вставь весь этот файл и нажми ▶.
# Скрипт спросит api_id, api_hash, номер телефона, код из Telegram и (если включён) облачный пароль.
# В конце напечатает длинную строку: это TG_SESSION для GitHub. Никому её не показывай.
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = int(input('api_id: ').strip())
api_hash = input('api_hash: ').strip()

client = TelegramClient(StringSession(), api_id, api_hash)
await client.start()
me = await client.get_me()
print(f'\nВошёл как {me.first_name} (@{me.username}). Это TG_SESSION:\n')
print(client.session.save())
await client.disconnect()
