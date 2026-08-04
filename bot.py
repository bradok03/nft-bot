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
BOT_TOKEN = os.getenv("BOT_TOKEN")          # Токен берётся из переменных окружения
ADMIN_ID = 8921066517
BUYER_USERNAME = "@skaence"
# ===============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class SellNFT(StatesGroup):
    username = State()
    price = State()
    description = State()
    confirm = State()


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Ты хочешь продать NFT.\n\n"
        "Отправь свой <b>юзернейм</b> (куда потом переводить деньги),\n"
        "например: @username",
        parse_mode="HTML"
    )
    await state.set_state(SellNFT.username)


@dp.message(SellNFT.username)
async def process_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await message.answer("Теперь укажи <b>цену</b> (например: 150 TON или 5000 руб):", parse_mode="HTML")
    await state.set_state(SellNFT.price)


@dp.message(SellNFT.price)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    await message.answer("Теперь напиши <b>описание NFT</b>:", parse_mode="HTML")
    await state.set_state(SellNFT.description)


@dp.message(SellNFT.description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    data = await state.get_data()

    text = (
        f"<b>Проверь заявку:</b>\n\n"
        f"Юзернейм: <code>{data['username']}</code>\n"
        f"Цена: <b>{data['price']}</b>\n"
        f"Описание: {data['description']}\n\n"
        f"Всё верно?"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")
        ]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(SellNFT.confirm)


@dp.callback_query(SellNFT.confirm, F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    seller = callback.from_user

    admin_text = (
        f"<b>Новая заявка на продажу NFT</b>\n\n"
        f"От: {seller.full_name} (@{seller.username or 'нет'})\n"
        f"ID продавца: <code>{seller.id}</code>\n\n"
        f"Юзернейм для оплаты: <code>{data['username']}</code>\n"
        f"Цена: <b>{data['price']}</b>\n"
        f"Описание: {data['description']}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept:{seller.id}"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject:{seller.id}")
        ]
    ])

    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")
    await callback.message.edit_text("✅ Заявка отправлена покупателю. Ожидай решения.")
    await state.clear()
    await callback.answer()


@dp.callback_query(SellNFT.confirm, F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Заявка отменена.")
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def accept_deal(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])

    await bot.send_message(
seller_id,
        f"Покупатель ({BUYER_USERNAME}) оплатил заказ.\n\n"
        f"После отправки NFT вы получите деньги."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Ты согласился</b>",
        parse_mode="HTML"
    )
    await callback.answer("Продавцу отправлено уведомление об оплате")


@dp.callback_query(F.data.startswith("reject:"))
async def reject_deal(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])

    await bot.send_message(
        seller_id,
        "К сожалению, покупатель отказался от вашей заявки."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Ты отказался</b>",
        parse_mode="HTML"
    )
    await callback.answer("Продавцу отправлено уведомление об отказе")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
