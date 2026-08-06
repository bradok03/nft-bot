import asyncio
import logging
import os
import uuid
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8921066517
CARD_NUMBER = "2200701222848878"
# ===============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

registered_users = {}
deals = {}


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

    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Техподдержка")]],
        resize_keyboard=True
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Продать NFT", callback_data="role_sell")],
        [InlineKeyboardButton(text="💰 Купить NFT", callback_data="role_buy")]
    ])

    await message.answer(
        "<b>Добро пожаловать!</b>\n\n"
        "Выбери, что хочешь сделать:",
        reply_markup=inline_kb,
        parse_mode="HTML"
    )
    await message.answer(" ", reply_markup=reply_kb)


@dp.message(F.text == "Техподдержка")
async def support(message: Message):
    await message.answer("Техподдержка: @skaence")


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

    deal_id = str(uuid.uuid4())[:8]

    if role == "sell":
        seller_id = user.id
        buyer_id = registered_users.get(other_username_clean)
    else:
        seller_id = registered_users.get(other_username_clean)
        buyer_id = user.id

    deals[deal_id] = {
        "role": role,
        "sender_id": user.id,
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "price": data["price"],
        "nft_name": data["nft_name"],
        "paid": False,
        "nft_sent": False
    }

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
            InlineKeyboardButton(text="✅ Согласиться", callback_data=f"accept:{deal_id}"),
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject:{deal_id}")
        ]
    ])

    await bot.send_message(ADMIN_ID, deal_text, reply_markup=kb, parse_mode="HTML")

    other_id = registered_users.get(other_username_clean)
    status = ["Заявка отправлена."]

    if other_id:
        try:
            await bot.send_message(other_id, deal_text, reply_markup=kb, parse_mode="HTML")
            if role == "sell":
                status.append("Также отправлена покупателю.")
            else:
                status.append("Также отправлена продавцу.")
        except Exception:
            status.append("Вторая сторона недоступна.")
    else:
        if role == "sell":
            status.append("Покупатель ещё не запускал бота.")
        else:
            status.append("Продавец ещё не запускал бота.")

    await callback.message.edit_text("✅ " + " ".join(status))
    await state.clear()
    await callback.answer()


@dp.callback_query(Form.confirm, F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Заявка отменена.")
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data.startswith("accept:"))
async def accept_deal(callback: CallbackQuery):
    deal_id = callback.data.split(":")[1]
    deal = deals.get(deal_id)

    if not deal:
        await callback.answer("Заявка устарела", show_alert=True)
        return

    sender_id = deal["sender_id"]
    price = deal["price"]

    payment_text = (
        f"<b>Заявка принята!</b>\n\n"
        f"Для оплаты переведите <b>{price}</b> на карту:\n\n"
        f"<code>{CARD_NUMBER}</code>\n\n"
        f"⚠️ Деньги будут на удержании и будут отправлены только в течение 7 дней.\n\n"
        f"После перевода нажмите кнопку ниже."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я отправил деньги", callback_data=f"paid:{deal_id}")]
    ])

    await bot.send_message(sender_id, payment_text, reply_markup=kb, parse_mode="HTML")

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Ты согласился</b>",
        parse_mode="HTML"
    )
    await callback.answer("Реквизиты отправлены")


@dp.callback_query(F.data.startswith("paid:"))
async def user_paid(callback: CallbackQuery):
    deal_id = callback.data.split(":")[1]
    deal = deals.get(deal_id)

    if not deal:
        await callback.answer("Заявка устарела", show_alert=True)
        return

    deal["paid"] = True
    seller_id = deal.get("seller_id")

    # Отправляем продавцу сообщение + кнопку
    if seller_id:
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я отправил NFT", callback_data=f"nft_sent:{deal_id}")]
            ])
            await bot.send_message(
                seller_id,
                "Покупатель оплатил заказ.\n\n"
                "Отправьте NFT администратору @skaence на удержание.\n\n"
                "После отправки нажмите кнопку ниже.",
                reply_markup=kb
            )
        except Exception:
            pass

    await bot.send_message(
        ADMIN_ID,
        f"Пользователь нажал «Я отправил деньги» (сделка {deal_id}).\n"
        f"Ожидается отправка NFT администратору @skaence."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Отмечено: деньги отправлены</b>",
        parse_mode="HTML"
    )
    await callback.answer("Готово")

    # Проверяем, не завершена ли уже сделка
    await check_deal_complete(deal_id)


@dp.callback_query(F.data.startswith("nft_sent:"))
async def nft_sent(callback: CallbackQuery):
    deal_id = callback.data.split(":")[1]
    deal = deals.get(deal_id)

    if not deal:
        await callback.answer("Заявка устарела", show_alert=True)
        return

    deal["nft_sent"] = True

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Отмечено: NFT отправлен</b>",
        parse_mode="HTML"
    )
    await callback.answer("Готово")

    await bot.send_message(
        ADMIN_ID,
        f"Продавец нажал «Я отправил NFT» (сделка {deal_id})."
    )

    await check_deal_complete(deal_id)


async def check_deal_complete(deal_id: str):
    deal = deals.get(deal_id)
    if not deal:
        return

    if deal.get("paid") and deal.get("nft_sent"):
        seller_id = deal.get("seller_id")
        buyer_id = deal.get("buyer_id")

        if seller_id:
            try:
                await bot.send_message(
                    seller_id,
                    "Вы получите деньги в течение 7 дней."
                )
            except Exception:
                pass

        if buyer_id:
            try:
                await bot.send_message(
                    buyer_id,
                    "Вы получите NFT в течение 7 дней."
                )
            except Exception:
                pass

        await bot.send_message(
            ADMIN_ID,
            f"Сделка {deal_id} полностью завершена обеими сторонами."
        )

        # Можно удалить сделку
        deals.pop(deal_id, None)


@dp.callback_query(F.data.startswith("reject:"))
async def reject_deal(callback: CallbackQuery):
    deal_id = callback.data.split(":")[1]
    deal = deals.get(deal_id)

    if not deal:
        await callback.answer("Заявка устарела", show_alert=True)
        return

    sender_id = deal["sender_id"]

    await bot.send_message(
        sender_id,
        "К сожалению, вторая сторона отказалась от вашей заявки."
    )

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Ты отказался</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отказ отправлен")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
