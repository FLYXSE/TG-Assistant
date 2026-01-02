import asyncio
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher(storage=MemoryStorage())

dp.message.filter(F.from_user.id == ADMIN_ID)
dp.callback_query.filter(F.from_user.id == ADMIN_ID)


class PostState(StatesGroup):
    text = State()
    media = State()
    buttons = State()
    confirm = State()


def parse_buttons(raw: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for line in raw.splitlines():
        if not line.strip():
            continue

        row = []
        parts = line.split("|")

        for part in parts[:8]:
            text, url = part.split(" - ", 1)
            row.append(
                InlineKeyboardButton(
                    text=text.strip(),
                    url=url.strip()
                )
            )

        rows.append(row)
        if len(rows) >= 15:
            break

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def send_post(
    *,
    chat_id: int,
    text: str,
    media: Message | None,
    buttons: InlineKeyboardMarkup
):
    if media:
        if media.photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=media.photo[-1].file_id,
                caption=text,
                reply_markup=buttons
            )
        elif media.video:
            await bot.send_video(
                chat_id=chat_id,
                video=media.video.file_id,
                caption=text,
                reply_markup=buttons
            )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=buttons
        )


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🧅 Дароу!\n\n"
        "Команды:\n"
        "/post — создать пост"
        "\nБот создан @kwiken | @Onion_vf"
    )


@dp.message(Command("post"))
async def post_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✍️ Отправь текст поста:")
    await state.set_state(PostState.text)


@dp.message(PostState.text)
async def post_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("📎 Отправь фото/видео или напиши /skip")
    await state.set_state(PostState.media)


@dp.message(PostState.media)
async def post_media(message: Message, state: FSMContext):
    if message.text == "/skip":
        await state.update_data(media=None)
    else:
        await state.update_data(media=message)

    await message.answer(
        "🔘 Отправь кнопки:\n\n"
        "Кнопка 1 - http://link.com | Кнопка 2 - http://link.com\n\n"
        "До 8 кнопок в ряд, до 15 рядов"
    )
    await state.set_state(PostState.buttons)


@dp.message(PostState.buttons)
async def post_buttons(message: Message, state: FSMContext):
    buttons = parse_buttons(message.text)
    await state.update_data(buttons=buttons)

    data = await state.get_data()

    await message.answer("👀 Предпросмотр:")

    await send_post(
        chat_id=message.chat.id,
        text=data["text"],
        media=data["media"],
        buttons=buttons
    )

    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать",
                    callback_data="publish"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel"
                )
            ]
        ]
    )

    await message.answer(
        "Подтвердить публикацию?",
        reply_markup=confirm_kb
    )

    await state.set_state(PostState.confirm)


@dp.callback_query(F.data.in_(["publish", "cancel"]))
async def post_confirm(call: CallbackQuery, state: FSMContext):
    if call.data == "cancel":
        await call.message.edit_text("❌ Публикация отменена")
        await state.clear()
        return

    data = await state.get_data()

    await send_post(
        chat_id=CHANNEL_ID,
        text=data["text"],
        media=data["media"],
        buttons=data["buttons"]
    )

    await call.message.edit_text("🚀 Пост опубликован")
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Assistant Запущен!")
    asyncio.run(main())
