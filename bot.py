import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8921066517
CARD_NUMBER = "2200701222848878"
# ===============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# username (lower) → user_id
registered_users = {}


class Form(StatesGroup):
    role = State()
    my_username = State()
    other_username = State()
    nft_name = State()
    price = State()
    confirm = State()


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    if message.from_user.username:
        registered_users[message.from_user.username.lower()] = message.from_user.id

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Продать NFT", callback_data="role_sell")],
        [InlineKeyboardButton(text="💰 Купить NFT", callback_data="role_buy")]
    ])

    await message.answer(
        "<b>Добро пожаловать!</b>\n\n"
        "Выбери, что хочешь сделать:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@dp.callback_query(F.data.in_({"role_sell", "role_buy"}))
async def choose_role(callback: CallbackQuery, state: FSMContext):
    role = "sell" if callback.data == "role_sell" else "buy"
    await state.update_data(role=role)

    action = "продать" if role == "sell" else "купить"

    await callback.message.edit_text(
        f"Ты хочешь <b>{action}</b> NFT.\n\n"
        f"Отправь <b>свой юзернейм</b>:\n"
        f"Например: @username",
        parse_mode="HTML"
    )
    await state.set_state(Form.my_username)
    await callback.answer()


@dp.message(Form.my_username)
async def process_my_username(message: Message, state: FSMContext):
    await state.update_data(my_username=message.text.strip())
    data = await state.get_data()

    other = "покупателя" if data["role"] == "sell" else "продавца"

    await message.answer(
        f"Теперь напиши <b>юзернейм {other}</b>:\n"
        f"Например: @username",
        parse_mode="HTML"
    )
    await state.set_state(Form.other_username)


@dp.message(Form.other_username)
async def process_other_username(message: Message, state: FSMContext):
    await state.update_data(other_username=message.text.strip())
    await message.answer("Теперь напиши <b>название NFT</b>:", parse_mode="HTML")
    await state.set_state(Form.nft_name)


@dp.message(Form.nft_name)
async def process_nft_name(message: Message, state: FSMContext):
    await state.update_data(nft_name=message.text.strip())
    await message.answer("Теперь укажи <b>цену</b> (например: 1500 ₽):", parse_mode="HTML")
    await state.set_state(Form.price)


@dp.message(Form.price)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    data = await state.get_data()

    role_text = "Продажа" if data["role"] == "sell" else "Покупка"

    text = (
        f"<b>Проверь заявку ({role_text}):</b>\n\n"
        f"Твой юзернейм: <code>{data['my_username']}</code>\n"
        f"Юзернейм второй стороны: <code>{data['other_username']}</code>\n"
        f"Название NFT: <b>{data['nft_name']}</b>\n"
        f"Цена: <b>{data['price']}</b>\n\n"
        f"Всё верно?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")
        ]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(Form.confirm)


@dp.callback_query(Form.confirm, F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user

    role = data["role"]
    role_text = "продажу" if role == "sell" else "покупку"
    other_username_clean = data["other_username"].lstrip("@").lower()

    deal_text = (
        f"<b>Новая заявка на {role_text} NFT</b>\n\n"
        f"От: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\n\n"
        f"Юзернейм отправителя: <code>{data['my_username']}</code>\n"
        f"Юзернейм второй стороны: <code>{data['other_username']}</code>\n"
        f"Название NFT: <b>{data['nft_name']}</b>\n"
        f"Цена: <b>{data['price']}</b>"
    )

    # В callback сохраняем роль и id отправителя
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept:{user.id}:{role}"),
            InlineKeyboardButton(text="❌
