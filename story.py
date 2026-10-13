"""
Публикует сториз в Telegram-канал от имени личного аккаунта (Bot API так не умеет).

Берёт видео из уже опубликованного поста канала (номер поста приходит из Google-таблицы)
и выкладывает его в сториз канала. Запускается в GitHub Actions, см. .github/workflows/story.yml.
"""
import asyncio
import json
import os
import random
import subprocess
import sys
import tempfile

from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.tl import functions, types

CHANNEL = 'producer_chmonya'
MAX_SECONDS = 60  # Telegram не принимает в сториз видео длиннее минуты

FRIENDLY = {
    'BOOSTS_REQUIRED': 'каналу не хватает бустов для сториз',
    'STORIES_TOO_MUCH': 'достигнут лимит сториз в сутки',
    'CHAT_ADMIN_REQUIRED': 'аккаунт не админ канала или у него нет права публиковать сториз',
    'STORY_PERIOD_INVALID': 'неверный срок жизни сториз',
}


def probe(path):
    out = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=width,height:format=duration', '-of', 'json', path],
        check=True, capture_output=True, text=True).stdout
    info = json.loads(out)
    stream = info['streams'][0]
    return float(info['format']['duration']), int(stream['width']), int(stream['height'])


def trim(path, seconds):
    out = path + '.story.mp4'
    subprocess.run(
        ['ffmpeg', '-y', '-v', 'error', '-i', path, '-t', str(seconds),
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out],
        check=True)
    return out


async def main():
    raw_id = os.environ.get('MESSAGE_ID', '').strip()
    if not raw_id.isdigit():
        sys.exit(f'Нужен номер поста в канале, получено: {raw_id!r}')
    message_id = int(raw_id)

    client = TelegramClient(StringSession(os.environ['TG_SESSION']),
                            int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'])
    await client.connect()
    if not await client.is_user_authorized():
        sys.exit('Сессия Telegram недействительна: заново получи TG_SESSION (login.py) и обнови секрет.')

    channel = await client.get_entity(CHANNEL)
    msg = await client.get_messages(channel, ids=message_id)
    if not msg or not msg.video:
        sys.exit(f'В посте {message_id} канала @{CHANNEL} нет видео.')

    with tempfile.TemporaryDirectory() as tmp:
        path = await client.download_media(msg, file=os.path.join(tmp, 'video.mp4'))
        duration, w, h = probe(path)
        if duration > MAX_SECONDS:
            print(f'Видео {duration:.0f} с, обрезаю до {MAX_SECONDS} с')
            path = trim(path, MAX_SECONDS)
            duration, w, h = probe(path)

        uploaded = await client.upload_file(path)
        media = types.InputMediaUploadedDocument(
            file=uploaded, mime_type='video/mp4',
            attributes=[types.DocumentAttributeVideo(
                duration=duration, w=w, h=h, supports_streaming=True)])
        try:
            res = await client(functions.stories.SendStoryRequest(
                peer=channel, media=media,
                privacy_rules=[types.InputPrivacyValueAllowAll()],
                random_id=random.getrandbits(63)))
        except errors.RPCError as e:
            reason = FRIENDLY.get(e.message, e.message)
            sys.exit(f'Telegram не принял сториз: {reason}')

    story_id = next((u.id for u in getattr(res, 'updates', [])
                     if isinstance(u, types.UpdateStoryID)), None)
    link = f'https://t.me/{CHANNEL}/s/{story_id}' if story_id else 'опубликовано'
    print(f'Сториз из поста {message_id}: {link}')
    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
