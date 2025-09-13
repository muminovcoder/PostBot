import asyncio
import html
import json
import logging
import os
import random
import re
from datetime import datetime, timezone, timedelta
from functools import wraps
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, Message, \
    CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

TOKEN = "7217822558:AAHVsJJO-ML4tR_F5pI21JjeoyHwV4DzGhw"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

USERS_FILE = 'user.json'
POSTS_FILE = 'Post.json'
posts = {}
post_data = {}
json_file_path = 'favorite.json'
USER_DATA_FILE = "user_data.json"
ADMINS = [6891895481,6096089345]
start_time = datetime.now(timezone.utc)
CHANNELS = []

def generate_post_id():
    return str(random.randint(10000, 99999))

def load_user_data():
    if not os.path.exists("user_data.json"):
        with open("user_data.json", "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=4)
    try:
        with open("user_data.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return []

# 🔹 Foydalanuvchilar ro‘yxatini saqlash
def save_user_data(data):
    with open("user_data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

# 🔹 Foydalanuvchini qo‘shish funksiyasi
def add_user(user_id):
    data = load_user_data()
    if user_id not in data:
        data.append(user_id)
        save_user_data(data)

user_data = load_user_data()

async def check_subscription(user_id: int):
    not_subscribed_channels = []
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed_channels.append(channel)
        except TelegramBadRequest as e:
            logging.error(f"Error checking subscription for {channel}: {e}")
            not_subscribed_channels.append(channel)
        except Exception as e:
            logging.warning(f"Unexpected error checking subscription for {channel}: {e}")
    return not_subscribed_channels

async def prompt_subscription(message: types.Message, not_subscribed_channels):
    buttons = [
        [InlineKeyboardButton(text="➕ Obuna bo‘ling", url=f"https://t.me/{channel[1:]}")]
        for channel in not_subscribed_channels
    ]
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "<b>📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

def subscription_required(handler):
    @wraps(handler)
    async def wrapper(message: types.Message, *args, **kwargs):
        not_subscribed_channels = await check_subscription(message.from_user.id)
        if not_subscribed_channels:
            await prompt_subscription(message, not_subscribed_channels)
        else:
            return await handler(message, *args, **kwargs)

    return wrapper

class MediaState(StatesGroup):
    waiting_for_media = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    add_user(user_id)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Post yaratish")],
            [KeyboardButton(text="🔗 Link (Post)")],
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="ℹ️ Haqida"), KeyboardButton(text="📎 Media ID")],
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"""
👋 Assalomu alaykum, <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a>! 😊

🎨 Post yaratish va ulashishning eng oson yo‘li!

🚀 Ijodiy g‘oyalaringizni chiroyli va ta’sirchan postga aylantirishda yordam beraman!

🔥 Sizning postlaringizni yanada jozibali va e’tiborni tortadigan qilishimiz mumkin!

🔗 Post yaratish uchun: 👉 <a href='https://t.me/Create_postuz_bot'>Post Uz Bot</a>
        """,
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@dp.message(F.text == "📎 Media ID")
async def request_media(message: Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Ortga")]], resize_keyboard=True
    )
    await message.answer("📥 Iltimos, rasm, video, GIF, audio, hujjat yoki matn yuboring:", reply_markup=keyboard)
    await state.set_state(MediaState.waiting_for_media)

@dp.message(MediaState.waiting_for_media)
async def get_media_id(message: Message, state: FSMContext):
    media_id = None
    media_type = None
    file_size = None
    file_name = None

    # 🕒 Xabar vaqti (to'g'ri ishlashi uchun)
    message_time = message.date.strftime("%Y-%m-%d %H:%M:%S")

    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "📸 Rasm"
        file_size = message.photo[-1].file_size
    elif message.video:
        media_id = message.video.file_id
        media_type = "🎬 Video"
        file_size = message.video.file_size
        file_name = message.video.file_name if message.video.file_name else None
    elif message.animation:
        media_id = message.animation.file_id
        media_type = "🎞 GIF"
        file_size = message.animation.file_size
    elif message.document:
        media_id = message.document.file_id
        media_type = "📄 Hujjat"
        file_size = message.document.file_size
        file_name = message.document.file_name
    elif message.audio:
        media_id = message.audio.file_id
        media_type = "🎵 Audio"
        file_size = message.audio.file_size
        file_name = message.audio.file_name
    elif message.voice:
        media_id = message.voice.file_id
        media_type = "🎙 Ovozli xabar"
        file_size = message.voice.file_size
    elif message.text:
        media_id = message.message_id
        media_type = "📝 Matn"

    file_size_text = f"\n📏 Hajmi: {round(file_size / 1024, 2)} KB" if file_size else ""
    file_name_text = f"\n🏷 Fayl nomi: <code>{file_name}</code>" if file_name else ""

    if media_id:
        # 🔥 `#` belgisini formatlash uchun `<code>#</code>` yoki `\#` ishlatilmoqda
        media_id_text = f"<code>{media_id}</code>".replace("#", "🔹")

        await message.answer(
            f"{media_type} uchun Media ID:\n\n"
            f"🔹 {media_id_text}\n"
            f"⏳ Xabar vaqti: {message_time}{file_size_text}{file_name_text}\n\n"
            "📝 **ID ni nusxalash:**\n"
            "- ID ustiga bosing va nusxa oling! 📋",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Noto‘g‘ri format! Iltimos, media yoki matn yuboring.")

    await state.clear()



# 🔙 Ortga qaytish
@dp.message(F.text == "🔙 Ortga")
async def back_to_main(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Post yaratish")],
            [KeyboardButton(text="🔗 Link (Post)")],
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="ℹ️ Haqida"), KeyboardButton(text="📎 Media ID")],
        ],
        resize_keyboard=True
    )
    await message.answer("🏠 Asosiy menyuga qaytdingiz!", reply_markup=keyboard)


@dp.message(F.text == "🔙 Ortga")
async def back_to_main_menu(message: types.Message):
    """ Foydalanuvchini asosiy menyuga qaytarish """
    await start(message)  # Start funksiyasini qayta chaqirib, asosiy menyuni ochib beradi


@dp.message(Command("menu"))
async def menu(message: types.Message):
    user_id = message.from_user.id

    not_subscribed_channels = await check_subscription(user_id)
    if not_subscribed_channels:
        await prompt_subscription(message, not_subscribed_channels)
        return

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Post yaratish")],
            [KeyboardButton(text="🔗 Link (Post)")],
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="ℹ️ Haqida"), KeyboardButton(text="📎 Media ID")],
        ],
        resize_keyboard=True
    )

    await message.answer(
"<b>Bosh menuga Xush kelibsiz</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
        disable_web_page_preview=True
    )



START_TIME = datetime.now()

@dp.message(F.text == "📊 Statistika")
@subscription_required
async def show_statistics(message: types.Message):
    total_users = len(user_data)  # Umumiy foydalanuvchilar soni

    # ⏳ Ishlash vaqtini hisoblash
    now = datetime.now()
    uptime = now - START_TIME

    days, seconds = divmod(uptime.total_seconds(), 86400)  # Kun va qolgan soniyalar
    hours, seconds = divmod(seconds, 3600)  # Soat va qolgan soniyalar
    minutes, seconds = divmod(seconds, 60)  # Daqiqa va soniya

    # 📊 Statistika xabari
    msg = f"""
📊 <b>Statistika</b>

👥 <b>Umumiy foydalanuvchilar:</b> <b>{total_users}</b> ta  
🚀 <b>Bot ishga tushgan sana:</b> <b>{START_TIME.strftime('%Y-%m-%d')}</b>  
⏱ <b>Bot ishga tushgan vaqt:</b> <b>{START_TIME.strftime('%H:%M:%S')}</b>  
⏳ <b>Bot ishlayotgan vaqt:</b> <b>{int(days)} kun, {int(hours)} soat, {int(minutes)} daqiqa, {int(seconds)} soniya</b>
    """
    await message.answer(msg, parse_mode="HTML")
@dp.callback_query(F.data == "check_subscription")
async def verify_subscription(call: types.CallbackQuery):
    user_id = call.from_user.id
    not_subscribed_channels = await check_subscription(user_id)

    if not_subscribed_channels:
        await prompt_subscription(call.message, not_subscribed_channels)
    else:
        await call.message.edit_text(
            "✅ Tabriklaymiz! Siz barcha kanallarga obuna bo‘lgansiz.\n\n/start ni bosib davom eting.",
            reply_markup=None
        )
class PostState(StatesGroup):
    waiting_for_media = State()
    waiting_for_caption = State()
    waiting_for_button_count = State()
    waiting_for_button_name = State()
    waiting_for_button_link = State()
    waiting_for_post_name = State()

class Form(StatesGroup):
    add_channel = State()
    waiting_for_channel_username = State()

class Reklama(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()

class LinkPost(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_count = State()
    waiting_for_words = State()
    waiting_for_links = State()
    waiting_for_button_name = State()
    waiting_for_button_url = State()

def load_users():

    if not os.path.exists(USER_DATA_FILE) or os.stat(USER_DATA_FILE).st_size == 0:
        return []
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            if isinstance(users, list):
                return users
            elif isinstance(users, dict):
                return list(users.keys())
    except json.JSONDecodeError:
        return []
    return []

def load_posts():
    try:

        file_path = "Posts.json"

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return {}

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
            else:
                print("⚠️ Xatolik: Posts.json faylidagi ma'lumotlar noto'g'ri formatda!")
                return {}
    except json.JSONDecodeError:
        print("⚠️ Xatolik: Posts.json fayli noto'g'ri JSON formatida!")
        return {}
    except Exception as e:
        print(f"⚠️ Xatolik: {e}")
        return {}

def save_posts(data):
    with open("posts.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_json(file_path, default_value):
    try:
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            return default_value
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, type(default_value)) else default_value
    except json.JSONDecodeError:
        return default_value

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_user_id(user_id):
    users = load_json(USER_DATA_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USER_DATA_FILE, users)


@dp.message(lambda message: message.text == "⬅️ Orqaga")
@subscription_required

async def back_to_main(message: types.Message):

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Post yaratish")],
            [KeyboardButton(text="🔗 Link (Post)")],
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="ℹ️ Haqida"), KeyboardButton(text="📎 Media ID")],
        ],
        resize_keyboard=True
    )

    await message.answer("🔙 *Asosiy menyuga qaytdingiz.*", reply_markup=keyboard, parse_mode="Markdown")


@dp.message(F.text == "⬅️ Orqaga")
@subscription_required

async def go_back(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📩 Post yaratish")],
            [KeyboardButton(text="🔗 Link (Post)")],
            [KeyboardButton(text="🔍 Qidiruv")],
            [KeyboardButton(text="ℹ️ Haqida"), KeyboardButton(text="📎 Media ID")],
        ],
        resize_keyboard=True
    )

    await message.answer("🔙 Siz orqaga qaytdingiz.\n\nAsosiy menyudan bo‘limni tanlang:", reply_markup=keyboard)


@dp.message(lambda message: message.text == "/help")
@subscription_required

async def help_command(message: Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMINS  # Admin ekanligini tekshirish

    text = ("<b>🦾 BOT TUZILISHI</b>\n\n"
            "╔══════ 🔹 <b>ASOSIY BUYRUQLAR</b> ══════╗\n"
            "┃\n"
            "┣ 🟢 <b>/start</b> — Botni ishga tushirish\n"
            "┣ 🆘 <b>/help</b> — Buyruqlar haqida ma'lumot olish\n"
            "┃\n"
            "╠══════ 🔍 <b>QIDIRUV TIZIMI</b> ══════╣\n"
            "┃\n"
            "┣ 🔎 <b>Qidiruvni boshlash:</b>  👀\n"
            "┃   ┣ 📌 '🔍 Qidiruv' tugmasini bosing\n"
            "┃   ┣ 📎 Post ID ni kiriting va natijani oling\n"
            "┃\n"
            "╠══════ ⚙️ <b>Qo‘shimcha Funksiyalar</b> ══════╣\n"
            "┃\n"
            "┣ ⚡ <b>Tezkor ishlash</b> — Optimal tizim  🏎️\n"
            "┣ 🔒 <b>Xavfsizlik</b> — Maxfiy ma’lumotlar himoyasi\n"
            "┃\n")

    if is_admin:
        text += ("╠══════ 🔥 <b>Admin Buyruqlari</b> ══════╣\n"
                 "┃\n"
                 "┣ 📢 <b>/rek</b> — Reklama yuborish 📣\n"
                 "┣ 📊 <b>/status</b> — Bot holatini ko‘rish 📈\n"
                 "┣ 📜 <b>/logs</b> — Bot loglarini ko‘rish 🗂️\n"
                 "┣ ➕ <b>/addchan</b> — Kanal qo‘shish 🔗\n"
                 "┃\n"
                 "╚════════════════════════════════╝")

    await message.answer(text, parse_mode="HTML")


@dp.message(Command("status"))
async def get_status(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("🚫 *Bu komanda faqat adminlar uchun\\!*", parse_mode="MarkdownV2")
        return

    users = load_users()
    user_count = len(users)

    uptime_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
    uptime = str(timedelta(seconds=int(uptime_seconds)))
    server_time_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    status_message = (
        "📊 *Bot holati:* 📊\n\n"
        f"👥 *Foydalanuvchilar soni:* `{user_count}` ta\n"
        f"⏰ *Ish vaqti:* `{uptime}`\n"
        f"🌐 *Server vaqti \\(UTC\\):* `{server_time_utc}`\n\n"
        "🤖 *Bot holati:* Faol ✅ \n"
    )

    await message.answer(status_message, parse_mode="MarkdownV2")

@dp.message(lambda message: message.text == "👤 Men")
@subscription_required

async def show_user_profile(message: types.Message):
    user_id = str(message.from_user.id)
    full_name = message.from_user.full_name if message.from_user.full_name else "Noma'lum"
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    status = "🟢 Faol"
    user_link = f'<a href="tg://user?id={user_id}">{full_name}</a>'

    posts = load_posts()
    user_posts = posts.get(user_id, [])
    post_count = len(user_posts)

    profile_text = (
        "╔════════════════════════╗\n"
        "  🎭 <b>Sizning Profilingiz</b> 🎭\n"
        "╚════════════════════════╝\n\n"
        f"┣ 🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"┣ 👤 <b>Ism:</b> {user_link}\n"
        f"┣ 📛 <b>Username:</b> {username}\n"
        f"┣ 🟢 <b>Holat:</b> {status}\n"
        f"┣ 📌 <b>Umumiy postlar soni:</b> <code>{post_count} ta</code>\n"
        "╚════════════════════════╝\n\n"
        "💡 <i>Botdan faol foydalaning va ajoyib postlar yarating!</i> ✨"
    )

    photo_id = "AgACAgIAAxkBAAIISWfTCnIMeDy24GIBuvZhmoRROB17AALz8TEbEnyZSg2xyqQu7lG5AQADAgADeAADNgQ"
    await message.answer_photo(photo=photo_id, caption=profile_text, parse_mode="HTML")


@dp.message(Command("sstart"))
async def sstart_command(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("🚫 Bu komanda faqat adminlar uchun!")
        return

    # ✅ "🚀 Start" va "ℹ Help" tugmalari yaratildi
    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Start", callback_data="send_start_to_all")],
            [InlineKeyboardButton(text="ℹ Help", callback_data="send_help_to_all")]
        ]
    )

    await message.answer(
        "📢 *Barcha foydalanuvchilarga xabar yuborish uchun tugmalardan birini tanlang.*\n\n"
        "🚀 *Start:* Barcha foydalanuvchilarga /start yuborish.\n"
        "ℹ *Help:* Barcha foydalanuvchilarga /help yuborish.",
        parse_mode="Markdown",
        reply_markup=buttons  # ✅ Tugmalar birga chiqadi
    )


@dp.callback_query(F.data == "send_start_to_all")
async def send_start_to_all(callback: types.CallbackQuery):
    users = load_users()
    sent_count = 0
    failed_count = 0

    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text="/start")
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send /start to {user_id}: {e}")
            failed_count += 1

    await callback.answer(f"✅ {sent_count} ta foydalanuvchiga /start yuborildi!\n❌ {failed_count} ta yuborilmadi.")


@dp.callback_query(F.data == "send_help_to_all")
async def send_help_to_all(callback: types.CallbackQuery):
    users = load_users()
    sent_count = 0
    failed_count = 0

    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text="/help")
            sent_count += 1
        except Exception as e:
            logging.error(f"Failed to send /help to {user_id}: {e}")
            failed_count += 1

    await callback.answer(f"✅ {sent_count} ta foydalanuvchiga /help yuborildi!\n❌ {failed_count} ta yuborilmadi.")


@dp.message(Command("rek"))
async def rek_command(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        await message.answer("🚫 Bu komanda faqat adminlar uchun!")
        return

    # ✅ Start tugmasini to‘g‘ri formatda yaratish
    start_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Start", callback_data="send_start_to_all")]
        ]
    )

    await message.answer(
        "📢 *Reklama turini tanlang:*\n\n"
        "📝 Matn\n"
        "📷 Rasm\n"
        "🎥 Video (oddiy yoki dumaloq)\n"
        "🎵 Audio\n\n"
        "🔗 Tugmali reklama yuborish /url faqat https// usulida\n\n"
        "🔗 /url\n"
        "👆 Yuqoridagi turdagi mediasini yuboring.",
        parse_mode="Markdown"
    )
    await state.set_state(Reklama.waiting_for_media)



@dp.message(StateFilter(Reklama.waiting_for_media))
async def handle_media_reklama(message: types.Message, state: FSMContext):
    media_id, reklama_type = None, None
    caption = message.caption if message.caption else None

    if message.photo:
        media_id, reklama_type = message.photo[-1].file_id, "photo"
    elif message.video:
        media_id, reklama_type = message.video.file_id, "video"
    elif message.video_note:
        media_id, reklama_type = message.video_note.file_id, "video_note"
    elif message.audio:
        media_id, reklama_type = message.audio.file_id, "audio"
    elif message.text:
        await send_reklama_to_users(content=message.text)
        await state.clear()
        await message.answer("✅ Reklama foydalanuvchilarga yuborildi!")
        return

    if media_id:
        await state.update_data(media_id=media_id, type=reklama_type, caption=caption)
        await message.answer("📝 Qo'shimcha matn yuboring (agar bo'lmasa, \"yo'q\" deb yozing):")
        await state.set_state(Reklama.waiting_for_text)
    else:
        await message.answer("❌ Noto'g'ri ma'lumot yuborildi. Iltimos, qayta urinib ko'ring.")


@dp.message(StateFilter(Reklama.waiting_for_text))
async def handle_additional_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_id, reklama_type = data.get("media_id"), data.get("type")
    caption = data.get("caption")
    additional_text = None if message.text.lower() == "yo'q" else message.text.strip()
    caption = additional_text if additional_text else caption

    if media_id:
        await send_reklama_to_users(content=caption, **{reklama_type: media_id})
        await state.clear()
        await message.answer("✅ Reklama foydalanuvchilarga yuborildi!")
    else:
        await message.answer("❌ Noto'g'ri ma'lumot. Iltimos, qayta urinib ko'ring.")


async def send_reklama_to_users(content=None, **media):
    users = load_users()
    for user_id in users:
        try:
            if content and not media:
                await bot.send_message(chat_id=user_id, text=content)
            elif media:
                for key, file_id in media.items():
                    if key == "photo":
                        await bot.send_photo(chat_id=user_id, photo=file_id, caption=content)
                    elif key == "video":
                        await bot.send_video(chat_id=user_id, video=file_id, caption=content, supports_streaming=True)
                    elif key == "video_note":
                        await bot.send_video_note(chat_id=user_id, video_note=file_id)
                    elif key == "audio":
                        await bot.send_audio(chat_id=user_id, audio=file_id, caption=content)
        except Exception as e:
            logging.error(f"Failed to send reklama to {user_id}: {e}")
            users.remove(user_id)
            with open(USER_DATA_FILE, 'w', encoding="utf-8") as file:
                json.dump(users, file, ensure_ascii=False, indent=4)



@dp.message(Command("addchan"), F.from_user.id.in_(ADMINS))
async def add_channel_start(message: Message, state: FSMContext):
    try:
        await update_channel_list(message, state)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await add_channel_start(message, state)

@dp.callback_query(F.data == "add_channel", Form.add_channel)
async def add_channel_process(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Yangi kanal usernameni yuboring:")
        await state.set_state(Form.waiting_for_channel_username)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await add_channel_process(callback_query, state)

@dp.message(Form.waiting_for_channel_username)
async def process_channel_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith('@'):
        await message.reply("Kanal username @ belgisi bilan boshlanishi kerak!")
        return

    if username in CHANNELS:
        await message.reply("Bu kanal allaqachon ro'yxatda!")
    else:
        try:

            await bot.get_chat(username)
            CHANNELS.append(username)
            await update_channel_list(message, state)
        except Exception as e:
            await message.reply(f"Kanal topilmadi yoki botda admin huquqi yo'q!\nXatolik: {str(e)}")

@dp.callback_query(F.data.startswith("remove_channel:"), Form.add_channel)
async def confirm_remove_channel(callback_query: CallbackQuery, state: FSMContext):
    try:
        channel = callback_query.data.split(":")[1]
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Ha", callback_data=f"confirm_remove:{channel}")
        builder.button(text="❌ Yo'q", callback_data="cancel_remove")
        builder.button(text="⬅️ Orqaga", callback_data="back_to_main")
        builder.adjust(1)

        await callback_query.message.edit_text(
            f"Kanalni o'chirishni tasdiqlaysizmi?\n{channel}",
            reply_markup=builder.as_markup()
        )
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await confirm_remove_channel(callback_query, state)

@dp.callback_query(F.data.startswith("confirm_remove:"), Form.add_channel)
async def remove_channel(callback_query: CallbackQuery, state: FSMContext):
    try:
        channel = callback_query.data.split(":")[1]
        if channel in CHANNELS:
            CHANNELS.remove(channel)
            await callback_query.answer(f"Kanal o'chirildi: {channel}")
        else:
            await callback_query.answer("Kanal topilmadi!")
        await add_channel_start(callback_query.message, state)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await remove_channel(callback_query, state)


# O'chirishni bekor qilish
@dp.callback_query(F.data == "cancel_remove", Form.add_channel)
async def cancel_remove_channel(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.answer("O'chirish bekor qilindi")
        await add_channel_start(callback_query.message, state)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await cancel_remove_channel(callback_query, state)


# Orqaga qaytish
@dp.callback_query(F.data == "back_to_main", Form.add_channel)
async def back_to_main_menu(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.answer("Asosiy menyuga qaytildi")
        await add_channel_start(callback_query.message, state)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await back_to_main_menu(callback_query, state)


# Kanallar ro'yxatini yangilash va obunachilar sonini ko'rsatish
async def update_channel_list(message_or_callback, state: FSMContext):
    try:
        builder = InlineKeyboardBuilder()
        channels_info = []

        for channel in CHANNELS:
            try:
                count = await bot.get_chat_member_count(channel)
                channels_info.append(f"• {channel} - {count} ta")
            except Exception as e:
                logging.error(f"Kanalga kirishda xatolik: {channel} - {e}")
                channels_info.append(f"• {channel} - Soni aniqlanmadi")

        for channel in CHANNELS:
            builder.button(text=f"❌ {channel}", callback_data=f"remove_channel:{channel}")
        builder.button(text="➕ Kanal qo'shish", callback_data="add_channel")
        builder.button(text="⬅️ Orqaga", callback_data="back_to_main")
        builder.adjust(1)

        message_text = (
                "Majburiy obuna kanallari:\n\n" +
                "\n".join(channels_info) +
                "\n\nYangi kanal qo'shish uchun usernameni yuboring"
        )

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(
                message_text,
                reply_markup=builder.as_markup()
            )
        else:
            await message_or_callback.answer(
                message_text,
                reply_markup=builder.as_markup()
            )

        await state.set_state(Form.add_channel)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        await update_channel_list(message_or_callback, state)

def get_user_post_counts(user_id: str):
    user_posts_count = 0
    user_favorites_count = 0

    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            posts = json.load(f)
        user_posts_count = sum(1 for post in posts if str(post.get("author_id")) == user_id)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            favorites = json.load(f)
        user_favorites_count = len(favorites.get(user_id, []))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    return user_posts_count, user_favorites_count

@dp.message(F.text == "🔗 Link (Post)")
@subscription_required
async def add_link(message: types.Message, state: FSMContext):
    await message.answer(
        "<b>📌 Post uchun havola qo‘shish</b>\n\n"
        "📸 Iltimos, post uchun rasm yoki video yuboring yoki faqat matn ham yuborishingiz mumkin.\n\n"
        "➖ Agar rasm yoki video qo‘shmoqchi bo‘lsangiz, avval uni yuboring.\n"
        "✍️ Keyinchalik havola biriktirish uchun matn ichida link ham yozishingiz mumkin.",
        parse_mode="HTML"
    )
    await state.set_state(LinkPost.waiting_for_media)

@dp.message(LinkPost.waiting_for_media, F.photo | F.video)
async def receive_media(message: types.Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id
        await state.update_data(photo=photo_id)
    elif message.video:
        video_id = message.video.file_id  # For videos
        await state.update_data(video=video_id)

    await message.answer("📝 Endi post uchun matn yuboring.")
    await state.set_state(LinkPost.waiting_for_text)


@dp.message(LinkPost.waiting_for_text, F.text)
async def receive_text(message: types.Message, state: FSMContext):
    text = message.text
    word_count = len(text.split())

    if word_count < 2:
        await message.answer("❌ Matn juda qisqa! Kamida 2 ta so‘z bo‘lishi kerak.")
        return

    await state.update_data(text=text)

    buttons = [[InlineKeyboardButton(text=str(i), callback_data=f"count_{i}")] for i in
               range(1, min(8, word_count + 1))]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("🔢 Nechta so‘z/gapga link ulamoqchisiz?", reply_markup=markup)
    await state.set_state(LinkPost.waiting_for_count)


@dp.callback_query(F.data.startswith("count_"))
async def choose_word_count(callback: types.CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[1])
    await state.update_data(word_count=count, selected_words=[], selected_links=[])

    await callback.message.answer("🔤 Matndagi 1-so‘z yoki gapni kiriting.")
    await state.set_state(LinkPost.waiting_for_words)


@dp.message(LinkPost.waiting_for_words, F.text)
async def receive_words(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    word = message.text

    if word not in user_data['text']:
        await message.answer("❌ Bu so‘z/gap matnda yo‘q! Qayta urining.")
        return

    if word in user_data['selected_words']:
        await message.answer("⚠️ Bu so‘z/gap allaqachon tanlangan! Boshqasini kiriting.")
        return

    user_data['selected_words'].append(word)
    await state.update_data(selected_words=user_data['selected_words'])

    if len(user_data['selected_words']) == user_data['word_count']:
        await message.answer("🔗 Endi 1-linkni yuboring.")
        await state.set_state(LinkPost.waiting_for_links)
    else:
        await message.answer(f"📌 Endi {len(user_data['selected_words']) + 1}-so‘z yoki gapni kiriting.")


@dp.message(LinkPost.waiting_for_links, F.text)
async def receive_links(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    link = message.text

    if not link.startswith("http://") and not link.startswith("https://"):
        await message.answer("❌ Noto‘g‘ri link! Iltimos, to‘g‘ri formatda kiriting (https://example.com)")
        return

    user_data['selected_links'].append(link)
    await state.update_data(selected_links=user_data['selected_links'])

    if len(user_data['selected_links']) == user_data['word_count']:

        final_text = user_data['text']
        for word, link in zip(user_data['selected_words'], user_data['selected_links']):
            final_text = final_text.replace(word, f"<a href='{link}'>{word}</a>")

        await message.answer("🔘 Iltimos, tugma nomini kiriting:")
        await state.set_state(LinkPost.waiting_for_button_name)
    else:
        await message.answer(f"🔗 Endi {len(user_data['selected_links']) + 1}-linkni yuboring.")


@dp.message(LinkPost.waiting_for_button_name, F.text)
async def receive_button_name(message: types.Message, state: FSMContext):
    button_name = message.text
    await state.update_data(button_name=button_name)

    await message.answer("🔗 Endi tugmaning URL manzilini kiriting:")
    await state.set_state(LinkPost.waiting_for_button_url)


@dp.message(LinkPost.waiting_for_button_url, F.text)
async def receive_button_url(message: types.Message, state: FSMContext):
    button_url = message.text

    if not button_url.startswith("http://") and not button_url.startswith("https://"):
        await message.answer("❌ Noto‘g‘ri link! Iltimos, to‘g‘ri formatda kiriting (https://example.com)")
        return

    user_data = await state.get_data()
    button_name = user_data['button_name']
    chat_id = str(message.chat.id)
    post_id = generate_post_id()

    final_text = user_data['text']
    for word, link in zip(user_data['selected_words'], user_data['selected_links']):
        final_text = final_text.replace(word, f"<a href='{link}'>{word}</a>")

    # Matn oxiriga "Post Uz Bot" ni havolali qo'shish
    final_text += "\n\n<a href='https://t.me/Create_postuz_bot'>⚡️ Post Uz Bot</a>"

    button = InlineKeyboardButton(text=button_name, url=button_url)
    markup = InlineKeyboardMarkup(inline_keyboard=[[button]])

    sent_message = None

    if 'photo' in user_data:
        sent_message = await bot.send_photo(
            chat_id=message.chat.id,
            photo=user_data['photo'],
            caption=final_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        media_id = user_data['photo']
        media_type = "photo"

    elif 'video' in user_data:
        sent_message = await bot.send_video(
            chat_id=message.chat.id,
            video=user_data['video'],
            caption=final_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        media_id = user_data['video']
        media_type = "video"

    else:
        sent_message = await bot.send_message(
            chat_id=message.chat.id,
            text=final_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        media_id = None
        media_type = "text"

    if sent_message:
        posts = load_posts()

        if chat_id not in posts:
            posts[chat_id] = {}

        posts[chat_id][post_id] = {
            "media": media_id,
            "type": media_type,
            "caption": final_text,
            "button_count": 1,
            "buttons": [
                {
                    "name": button_name,
                    "link": button_url
                }
            ],
            "post_id": post_id
        }

        save_posts(posts)

        await message.answer(f"✅ Post muvaffaqiyatli saqlandi!\n"
                             f"🆔 Post ID: <code>{post_id}</code>", parse_mode="HTML")

    await state.clear()


@dp.message(F.text == "ℹ️ Haqida")
@subscription_required

async def about(message: types.Message):
    info = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "  🌟 <b><a href='https://t.me/Create_postuz_bot'>Post Yaratish Boti</a></b> 🌟\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 <b>BOT HAQIDA TO‘LIQ MA’LUMOT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 <b>Yaratuvchi:</b> <a href='tg://user?id=6891895481'>Muhammadsolixon Muminov</a>\n"
        "📅 <b>Ishga tushirilgan sana:</b> <i>2025-yil 19-iyun</i>\n"
        "🎯 <b>Asosiy vazifasi:</b> <i>Interaktiv va samarali Telegram postlar yaratish</i>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🚀 <b>Nega aynan <a href='https://t.me/Create_postuz_bot'>Post Uz Bot</a>?</b>\n\n"
        "✅ Postlaringizni chiroyli va tartibli qilish\n"
        "✅ Tugmalar qo‘shish va interaktivlik yaratish\n"
        "✅ Media bilan ishlash va dizaynni yaxshilash\n"
        "✅ Tayyor matnlardan foydalanib, vaqtni tejash\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💎 <b>Bot sizga quyidagi eksklyuziv imkoniyatlarni taqdim etadi:</b>\n\n"
        "🔹 *Bir nechta tugmalar* qo‘shish – Postlaringizni interaktiv qiling.\n"
        "🔹 *Maxsus formatlangan matn* – Chiroyli ko‘rinishga ega postlar yarating.\n"
        "🔹 *Yuqori sifatli media yuklash* – Rasm va videolar bilan ishlash.\n"
        "🔹 *Animatsion va GIF postlar* – Harakatlanuvchi media bilan ajralib turing.\n"
        "🔹 *Hashtag tizimi* – Postlarni tez topish va trendga chiqarish imkoniyati.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📜 <b>TAYYOR MATNLAR BO‘LIMI</b>\n\n"
        "🔹 Tayyor matnlar orqali qiziqarli postlar yozish osonlashadi.\n"
        "🔹 Bu bo‘limda kino, tarix, ilm-fan, qiziqarli faktlar va boshqa mavzulardagi matnlarni topishingiz mumkin.\n"
        "🔹 Post yozishda qiyinchilik bo‘lsa, tayyor matnlardan foydalaning!\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📞 <b>ALOQA VA QO‘LLAB-QUVVATLASH</b>\n\n"
        "📩 <b>Telegram:</b> <a href='https://t.me/Mr_Mominov'>@Mr_Mominov</a>\n"
        "📩 <b>Email:</b> <i>uzsenior0@gmail.com</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "  ✨ <b>Post yaratish hech qachon bu qadar oson bo‘lmagan!</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>Quyidagi tugmani bosib, hoziroq post yaratishni boshlang!</b> 🎯"
    )

    await message.answer(info, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(F.text == "📩 Post yaratish")
@subscription_required
async def create_post(message: types.Message, state: FSMContext):
    await message.answer(
        "<b>⚡️ Diqqat!</b>\n\n"
        "📌 Bu bot faqat <b>tugmalar</b> orqali ishlaydi. Matn kiritish yoki boshqa komandalar yuborish shart emas!\n\n"
        "✅ Endi post yaratish uchun <b>rasm yoki video</b> yuboring.",
        parse_mode="HTML"
    )

    await state.set_state(PostState.waiting_for_media)

@dp.message(F.photo | F.video, StateFilter(PostState.waiting_for_media))
async def receive_media(message: types.Message, state: FSMContext):
    user_id = str(message.chat.id)
    post_id = str(random.randint(10000, 99999))

    post_data[user_id] = {
        post_id: {
            "media": message.photo[-1].file_id if message.photo else message.video.file_id,
            "type": "photo" if message.photo else "video",
            "caption": "",
            "button_count": 0,
            "buttons": [],
            "post_id": post_id
        }
    }

    await message.answer("📜 Endi post uchun matn kiriting:")
    await state.set_state(PostState.waiting_for_caption)


@dp.message(StateFilter(PostState.waiting_for_caption))
async def receive_caption(message: types.Message, state: FSMContext):
    user_id = str(message.chat.id)
    post_id = list(post_data[user_id].keys())[0]

    post_data[user_id][post_id]["caption"] = message.text

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(i), callback_data=f"buttons_{i}") for i in range(1, 4)],
            [InlineKeyboardButton(text=str(i), callback_data=f"buttons_{i}") for i in range(4, 7)],
            [InlineKeyboardButton(text="❌ Yo‘q", callback_data="buttons_0")]
        ]
    )

    await message.answer("🔘 Postga nechta tugma qo‘shmoqchisiz?", reply_markup=keyboard)
    await state.set_state(PostState.waiting_for_button_count)

# 🔘 Tugma sonini tanlash
@dp.callback_query(F.data.startswith("buttons_"))
async def button_count(callback: types.CallbackQuery, state: FSMContext):
    count = int(callback.data.split("_")[1])
    user_id = str(callback.message.chat.id)
    post_id = list(post_data[user_id].keys())[0]

    post_data[user_id][post_id]["button_count"] = count
    post_data[user_id][post_id]["buttons"] = []

    if count == 0:
        await send_final_post(callback.message)
        await state.clear()
    else:
        await callback.message.edit_text(f"📝 {count} ta tugma qo‘shiladi. Endi birinchi tugma nomini kiriting:")
        await state.set_state(PostState.waiting_for_button_name)

@dp.message(StateFilter(PostState.waiting_for_button_name))
async def receive_button_name(message: types.Message, state: FSMContext):
    user_id = str(message.chat.id)
    post_id = list(post_data[user_id].keys())[0]

    post_data[user_id][post_id]["buttons"].append({"name": message.text, "link": None})
    await message.answer(f"🔗 \"{message.text}\" tugmasi uchun link kiriting:")
    await state.set_state(PostState.waiting_for_button_link)
# 🔍 URL ni tekshiruvchi regex shablon
URL_REGEX = re.compile(
    r"^(https?://|tg://|t\.me/|@)[\w\.\-/]+(\.[a-z]{2,})?$"
)


@dp.message(StateFilter(PostState.waiting_for_button_link))
async def receive_button_link(message: types.Message, state: FSMContext):
    user_id = str(message.chat.id)
    post_id = list(post_data[user_id].keys())[0]

    link = message.text.strip()

    if link.startswith("@"):
        link = f"https://t.me/{link[1:]}"

    # ✅ URL formatini tekshiramiz
    if not URL_REGEX.match(link):
        await message.answer(
            "🚫 <b>Noto‘g‘ri URL formati!</b>\n\n"
            "✅ Quyidagi formatlardan birini kiriting:\n"
            "• <code>https://example.com</code>\n"
            "• <code>http://example.com</code>\n"
            "• <code>t.me/channelname</code>\n",
            parse_mode="HTML"
        )
        return

    post_data[user_id][post_id]["buttons"][-1]["link"] = link

    if len(post_data[user_id][post_id]["buttons"]) < post_data[user_id][post_id]["button_count"]:
        await message.answer(f"📝 {len(post_data[user_id][post_id]['buttons']) + 1}-tugma nomini kiriting:")
        await state.set_state(PostState.waiting_for_button_name)
    else:
        await send_final_post(message)
        await state.clear()


async def send_final_post(message: types.Message, is_saved=False):
    user_id = str(message.chat.id)
    post_id = list(post_data[user_id].keys())[0]
    data = post_data[user_id][post_id]

    # HTMLga xavfsiz matn
    caption = data.get("caption", "")
    post_caption = f"<b>{html.escape(caption)}</b>" if caption else ""

    # Footer text (HTMLga moslashtirilgan)
    footer_text = '🔹 <a href="https://t.me/Create_postuz_bot ">⚡️ Post Uz Bot</a>'

    # Umumiy matn
    final_caption = post_caption + "\n" + footer_text

    # Tugmalar
    keyboard = None
    if data["buttons"]:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["name"], url=btn["link"])] for btn in data["buttons"]
            ]
        )

    # Media turiga qarab yuborish
    if data["type"] == "video":
        await bot.send_video(
            message.chat.id,
            data["media"],
            caption=final_caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        await bot.send_photo(
            message.chat.id,
            data["media"],
            caption=final_caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    # Post ma'lumotini saqlash
    post_info = (
        f"📌 <b>Post ma’lumoti:</b>\n"
        f"🆔 <b>Post ID:</b> <code>{data['post_id']}</code>\n"
        f"🖼 <b>Tur:</b> {data['type']}\n"
        f"📝 <b>Matn:</b> {post_caption if post_caption else 'Yo‘q'}\n"
        f"🔘 <b>Tugmalar soni:</b> {data['button_count']}\n"
    )
    if data["buttons"]:
        post_info += "<b>🔗 Tugmalar:</b>\n"
        for btn in data["buttons"]:
            post_info += f"  • <b>{btn['name']}</b> ➝ <a href='{btn['link']}'>{btn['link']}</a>\n"

    await message.answer(post_info, parse_mode="HTML", disable_web_page_preview=True)

    # Posts.json ga saqlash
    posts = load_posts()
    if user_id not in posts:
        posts[user_id] = {}
    posts[user_id][post_id] = {
        "media": data["media"],
        "type": data["type"],
        "caption": caption,
        "button_count": data["button_count"],
        "buttons": data["buttons"],
        "post_id": post_id
    }
    save_posts(posts)

class PostSearch(StatesGroup):
    waiting_for_post_id = State()

@dp.message(lambda message: message.text == "🔍 Qidiruv")
@subscription_required
async def search_post(message: Message, state: FSMContext):
    await message.answer(
        "<b>🔎 Qidiruv</b>\n\n"
        "📌 <b>Postni faqat uning ID raqami orqali qidirish mumkin!</b>\n\n"
        "🔢 Iltimos, kerakli postning ID raqamini kiriting:",
        parse_mode="HTML"
    )

    await state.set_state(PostSearch.waiting_for_post_id)
@dp.message()
async def send_searched_post(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == PostSearch.waiting_for_post_id.state:
        post_id = message.text.strip()
        posts = load_posts()
        user_id = str(message.from_user.id)

        found_post = None
        post_owner_id = None
        for owner_id, user_posts in posts.items():
            if post_id in user_posts:
                found_post = user_posts[post_id]
                post_owner_id = owner_id
                break

        if found_post:
            if post_owner_id == user_id:
                keyboard = None
                if found_post["buttons"]:
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text=btn["name"], url=btn["link"])]
                            for btn in found_post["buttons"]
                        ]
                    )

                caption_text = f"<b>{found_post.get('caption', '')}</b>\n\n<a href='https://t.me/Create_postuz_bot'>⚡️ Post Uz Bot</a>"

                if found_post["type"] == "video":
                    await bot.send_video(
                        message.chat.id, found_post["media"], caption=caption_text,
                        reply_markup=keyboard, parse_mode="HTML"
                    )
                else:
                    await bot.send_photo(
                        message.chat.id, found_post["media"], caption=caption_text,
                        reply_markup=keyboard, parse_mode="HTML"
                    )

                await message.answer("✨ <b>Post muvaffaqiyatli topildi!</b> 🎉", reply_markup=get_post_list_button())
            else:
                await message.answer("⚠️ <b>Xatolik!</b> Bu post sizga tegishli emas yoki ID noto‘g‘ri kiritildi.", parse_mode="HTML")

        else:
            await message.answer("⚠️ <b>Xatolik!</b> Kiritilgan ID bo‘yicha post topilmadi.", parse_mode="HTML")

        await state.clear()



@dp.callback_query(lambda c: c.data == "my_posts_list")
async def show_user_posts_list(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    posts = load_posts()
    await send_user_posts_list(callback_query.message, posts, user_id)


async def send_user_posts_list(message: Message, posts, user_id):
    user_posts = posts.get(user_id, {})
    post_count = len(user_posts)

    if not user_posts:
        await message.answer(
            "📭 <b>┏━━━✦━━━┛</b>\n"
            "<b>Sizda hozircha postlar mavjud emas.</b>\n"
            "<b>┏━━━✦━━━┛</b>\n\n"
            "🔹 <b>Yangi post yaratish</b>ni boshlash uchun pastdagi tugmani bosing ⬇️",
            parse_mode="HTML"
        )
        return

    sorted_posts = sorted(user_posts.items(), key=lambda x: x[0])
    chunk_size = 15
    chunks = [sorted_posts[i:i + chunk_size] for i in range(0, len(sorted_posts), chunk_size)]

    for index, chunk in enumerate(chunks):
        text = (
            f"📌 <b>Sizning postlaringiz ro‘yxati:</b>\n"
            f"📋 <b>Umumiy postlar soni:</b> <code>{post_count}</code>\n"
            f"👀 <b>Ko‘rsatilgan postlar:</b> <code>{len(chunk)}</code>\n"
        )

        for post_id, post in chunk:
            button_count = len(post.get("buttons", []))
            caption = post.get("caption", "Mavjud emas")
            caption = html.escape(caption[:50]) + "..." if len(caption) > 50 else html.escape(caption)
            text += (
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📎 <b>ID:</b> <code>{post_id}</code>\n"
                f"🔹 <b>Tur:</b> {html.escape(post['type'])}\n"
                f"📝 <b>Izoh:</b> {caption}\n"
                f"🔘 <b>Tugmalar soni:</b> {button_count}\n"
            )
        text += (
            "\n⚠️ <b><u>Eslatma:</u></b>\n"
            "• 🔍 <b>Postni ko‘rish uchun:</b> ‘Qidiruv’ tugmasini bosing.\n"
            "• ➖ O‘zingizga tegishli <b>ID</b>ni yuboring.\n"
            "• ✅ Shunda sizga aynan o‘zingiz yaratgan post taqdim etiladi.\n"
        )
        await message.answer(text, parse_mode="HTML")

        if index < len(chunks) - 1:
            await asyncio.sleep(0.7)

async def send_post(chat_id, post):
    keyboard = None
    if post["buttons"]:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=btn["name"], url=btn["link"])] for btn in post["buttons"]
            ]
        )

    if post["type"] == "video":
        await bot.send_video(chat_id, post["media"], caption=post.get("caption", ""), reply_markup=keyboard,
                             parse_mode="HTML")
    else:
        await bot.send_photo(chat_id, post["media"], caption=post.get("caption", ""), reply_markup=keyboard,
                             parse_mode="HTML")

def get_post_list_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Postlar ro‘yxati", callback_data="my_posts_list")]
        ]
    )
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
