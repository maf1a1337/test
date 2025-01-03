from telegram import ForceReply, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from database import add_user, get_user_info
from datetime import datetime

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало работы с ботом"""
    # Очищаем все данные контекста при старте
    context.user_data.clear()
    
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text(
            "⚠️ <b>Внимание!</b>\n\n"
            "Для использования бота необходимо установить username в настройках Telegram.\n\n"
            "<b>Как это сделать:</b>\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел «Изменить профиль»\n"
            "3. Добавьте имя пользователя (username)\n"
            "4. После установки username вернитесь и нажмите /start",
            parse_mode='HTML'
        )
        return

    # Проверяем, существует ли пользователь в базе данных
    existing_user = await get_user_info(user.id)
    
    # Добавляем пользователя только если его нет в базе
    if not existing_user:
        await add_user(
            user_id=user.id,
            username=user.username,
            connection_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    keyboard = [
        ['Создать коробку'],
        ['Присоединиться к коробке'],
        ['Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = (
        "🎄 <b>Добро пожаловать в Secret Santa Bot!</b> 🎅\n\n"
        "Этот бот поможет организовать тайный обмен подарками между друзьями, "
        "коллегами или членами семьи.\n\n"
        "📦 <b>Что вы можете сделать:</b>\n"
        "• Создать свою коробку для обмена подарками\n"
        "• Присоединиться к существующей коробке\n"
        "• Управлять своими коробками в настройках\n\n"
        "🎁 <b>Выберите действие из меню ниже:</b>"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Возвращаем ConversationHandler.END чтобы сбросить все активные состояния
    return ConversationHandler.END
