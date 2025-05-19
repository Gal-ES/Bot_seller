from dotenv import load_dotenv
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Загрузка переменных окружения
load_dotenv('.env')

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_ACTION, VIEWING_CATALOG, VIEWING_CART, CHECKOUT, SUPPORT = range(5)

# База данных товаров
products = {
    1: {"name": "Футболка", "price": 1500, "description": "Хлопковая футболка"},
    2: {"name": "Джинсы", "price": 3000, "description": "Классические джинсы"},
    3: {"name": "Кроссовки", "price": 5000, "description": "Спортивные кроссовки"},
}

# Хранилища данных
user_carts = {}
order_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом."""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} начал работу с ботом.")
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Каталог", callback_data='view_catalog')],
        [InlineKeyboardButton("🛒 Корзина", callback_data='view_cart')],
        [InlineKeyboardButton("📦 Мои заказы", callback_data='view_orders')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Приветствую, {user.first_name}!\nДобро пожаловать в наш магазин!",
        reply_markup=reply_markup
    )
    
    return SELECTING_ACTION

async def view_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показ каталога товаров."""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for product_id, product in products.items():
        keyboard.append(
            [InlineKeyboardButton(
                f"{product['name']} - {product['price']/100:.2f} руб.", 
                callback_data=f'product_{product_id}'
            )]
        )
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')])
    
    await query.edit_message_text(
        text="🛍️ Каталог товаров:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return VIEWING_CATALOG

async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показ информации о товаре."""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = products[product_id]
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить в корзину", callback_data=f'add_{product_id}')],
        [InlineKeyboardButton("🔙 Назад", callback_data='view_catalog')]
    ]
    
    await query.edit_message_text(
        text=f"🛍️ {product['name']}\n\n"
             f"💰 Цена: {product['price']/100:.2f} руб.\n\n"
             f"📝 Описание: {product['description']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return VIEWING_CATALOG

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавление товара в корзину."""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = products[product_id]
    
    # Добавление товара в корзину
    user_id = update.effective_user.id
    if user_id not in user_carts:
        user_carts[user_id] = {}
    user_carts[user_id][product_id] = user_carts[user_id].get(product_id, 0) + 1
    
    # Создание клавиатуры
    keyboard = [
        [InlineKeyboardButton("🛒 Перейти в корзину", callback_data='view_cart')],
        [InlineKeyboardButton("🛍️ Продолжить покупки", callback_data='view_catalog')]
    ]
    
    # Отправка сообщения
    await query.edit_message_text(
        text=f"✅ {product['name']} добавлен в корзину!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECTING_ACTION

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показ содержимого корзины."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cart = user_carts.get(user_id, {})
    
    if not cart:
        await query.edit_message_text(
            text="🛒 Ваша корзина пуста",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')]
            ]))
        return VIEWING_CART
    
    total = 0
    cart_text = "🛒 Ваша корзина:\n\n"
    for product_id, quantity in cart.items():
        product = products[product_id]
        item_total = product['price'] * quantity
        total += item_total
        cart_text += f"{product['name']} - {quantity} шт. × {product['price']/100:.2f} руб. = {item_total/100:.2f} руб.\n"
    
    cart_text += f"\n💵 Итого: {total/100:.2f} руб."
    
    # Создание кнопок для каждого товара в корзине
    product_buttons = [
        [InlineKeyboardButton(
            f"❌ Удалить {products[pid]['name']}", 
            callback_data=f'remove_{pid}'
        )] for pid in cart.keys()
    ]
    
    # Основные кнопки управления
    control_buttons = [
        [InlineKeyboardButton("🧹 Очистить корзину", callback_data='clear_cart')],
        [InlineKeyboardButton("✅ Оформить заказ", callback_data='checkout')],
        [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        text=cart_text,
        reply_markup=InlineKeyboardMarkup(product_buttons + control_buttons)
    )
    
    return VIEWING_CART

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Оформление заказа."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cart = user_carts.get(user_id, {})
    
    if not cart:
        await query.edit_message_text(text="🛒 Ваша корзина пуста!")
        return VIEWING_CART
    
    total = sum(products[pid]['price'] * qty for pid, qty in cart.items())
    
    # Сохранение корзины в user_data для подтверждения
    context.user_data['cart'] = cart.copy()
    
    # Создание клавиатуры
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить заказ", callback_data='confirm_order')],
        [InlineKeyboardButton("❌ Отменить", callback_data='cancel_order')]
    ]
    
    # Отправка сообщения
    await query.edit_message_text(
        text=f"💳 Оформление заказа\n\n"
             f"Товаров: {sum(cart.values())} шт.\n"
             f"Сумма: {total/100:.2f} руб.\n\n"
             f"Подтвердите заказ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CHECKOUT

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение заказа."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cart = context.user_data['cart']
    
    if user_id not in order_history:
        order_history[user_id] = []
    
    order_history[user_id].append({
        'items': cart.copy(),
        'total': sum(products[pid]['price'] * qty for pid, qty in cart.items()),
        'status': 'Завершен'
    })
    
    user_carts[user_id] = {}
    
    await query.edit_message_text(
        text="✅ Заказ успешно оформлен!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')],
            [InlineKeyboardButton("📦 Мои заказы", callback_data='view_orders')]
        ]))
    
    return SELECTING_ACTION

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка отмены заказа."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="❌ Оформление заказа отменено. Товары остались в корзине.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Корзина", callback_data='view_cart')],
            [InlineKeyboardButton("🛍️ Каталог", callback_data='view_catalog')]
        ])
    )
    return SELECTING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия и возврат в главное меню."""
    await update.message.reply_text(
        text="Действие отменено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 На главную", callback_data='back_to_main')]
        ])
    )
    return ConversationHandler.END

async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показ истории заказов."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    orders = order_history.get(user_id, [])
    
    if not orders:
        await query.edit_message_text(
            text="📦 У вас пока нет заказов",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')]
            ]))
        return SELECTING_ACTION
    
    orders_text = "📦 История заказов:\n\n"
    for i, order in enumerate(orders, 1):
        orders_text += f"Заказ #{i}\n"
        for pid, qty in order['items'].items():
            orders_text += f"- {products[pid]['name']} × {qty}\n"
        orders_text += f"Сумма: {order['total']/100:.2f} руб.\nСтатус: {order['status']}\n\n"
    
    await query.edit_message_text(
        text=orders_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ])
    )
    
    return SELECTING_ACTION

async def remove_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление одного товара из корзины."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    product_id = int(query.data.split('_')[1])
    
    if user_id in user_carts and product_id in user_carts[user_id]:
        del user_carts[user_id][product_id]
        if not user_carts[user_id]:  # Если корзина пуста
            del user_carts[user_id]
    
    await view_cart(update, context)  # Показ обновленной корзины
    return VIEWING_CART

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос подтверждения очистки корзины"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="⚠️ Вы уверены, что хотите очистить корзину?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, очистить", callback_data='confirm_clear')],
            [InlineKeyboardButton("❌ Нет, вернуться в корзину", callback_data='back_to_cart')]
        ])
    )
    return VIEWING_CART

async def confirm_clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение очистки корзины"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id in user_carts:
        del user_carts[user_id]
    
    await query.edit_message_text(
        text="🧹 Корзина успешно очищена!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')],
            [InlineKeyboardButton("🏠 На главную", callback_data='back_to_main')]
        ])
    )
    return SELECTING_ACTION  # Возврат в главное меню

async def back_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в корзину без очистки"""
    query = update.callback_query
    await query.answer()
    await view_cart(update, context)
    return VIEWING_CART

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Каталог", callback_data='view_catalog')],
        [InlineKeyboardButton("🛒 Корзина", callback_data='view_cart')],
        [InlineKeyboardButton("📦 Мои заказы", callback_data='view_orders')],
        [InlineKeyboardButton("🆘 Поддержка", callback_data='support')],
    ]
    
    await query.edit_message_text(
        text="Главное меню:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECTING_ACTION

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка запроса в поддержку."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📞 Поддержка\n\n"
             "Напишите ваш вопрос, и мы обязательно вам ответим.\n"
             "Просто отправьте сообщение в этот чат.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ])
    )
    return SUPPORT

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обратботка текстового сообщения для поддержки."""
    user = update.message.from_user
    message_text = update.message.text
    
    logger.info(f"Вопрос в поддержку от {user.full_name}: {message_text}")
    
    await update.message.reply_text(
        text="✅ Ваше сообщение получено! Спасибо за обращение.\n"
             "Наш менеджер ответит вам в ближайшее время.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ В каталог", callback_data='view_catalog')],
            [InlineKeyboardButton("🏠 На главную", callback_data='back_to_main')]
        ])
    )
    return SELECTING_ACTION

def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершение диалога."""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} отменил действие.")
    update.message.reply_text(
        'Действие отменено. Чтобы начать заново, нажмите /start',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("/start", callback_data='start')]
        ])
    )
    
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование ошибок."""
    logger.error(msg="Ошибка:", exc_info=context.error)
    
    if isinstance(update, Update):
        await update.message.reply_text('Произошла ошибка. Пожалуйста, попробуйте еще раз.')

def main():
    """Запуск бота."""
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        logger.error("❌ Токен не найден!")
        return
    
    try:
        # Создание Application
        application = Application.builder().token(TOKEN).build()
        
        # Настройка ConversationHandler
        conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        SELECTING_ACTION: [
            CallbackQueryHandler(view_catalog, pattern='^view_catalog$'),
            CallbackQueryHandler(view_cart, pattern='^view_cart$'),
            CallbackQueryHandler(view_orders, pattern='^view_orders$'),
            CallbackQueryHandler(support, pattern='^support$'),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
        ],
        VIEWING_CATALOG: [
            CallbackQueryHandler(view_product, pattern='^product_'),
            CallbackQueryHandler(add_to_cart, pattern='^add_'),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
        ],
        VIEWING_CART: [
            CallbackQueryHandler(remove_from_cart, pattern='^remove_'),
            CallbackQueryHandler(clear_cart, pattern='^clear_cart$'),
            CallbackQueryHandler(confirm_clear_cart, pattern='^confirm_clear$'),
            CallbackQueryHandler(back_to_cart, pattern='^back_to_cart$'),
            CallbackQueryHandler(view_catalog, pattern='^view_catalog$'),
            CallbackQueryHandler(checkout, pattern='^checkout$'),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
        ],
        CHECKOUT: [
            CallbackQueryHandler(confirm_order, pattern='^confirm_order$'),
            CallbackQueryHandler(cancel_order, pattern='^cancel_order$'),
        ],
        SUPPORT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message),
            CallbackQueryHandler(back_to_main, pattern='^back_to_main$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
        
        application.add_handler(conv_handler)
        application.add_error_handler(error_handler)
        
        logger.info("🤖 Бот запущен!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"🔴 Ошибка при запуске: {e}")

if __name__ == '__main__':
    main()