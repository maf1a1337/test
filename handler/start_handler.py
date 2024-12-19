from telegram import ForceReply, Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from database import add_user
from datetime import datetime

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало работы с ботом"""
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

    keyboard = [
        ['Создать коробку'],
        ['Присоединиться к коробке'],
        ['Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = (
        "🎄 *Добро пожаловать в Secret Santa Bot!* 🎅\n\n"
        "Этот бот поможет организовать тайный обмен подарками между друзьями, "
        "коллегами или членами семьи.\n\n"
        "📦 *Что вы можете сделать:*\n"
        "• Создать свою коробку для обмена подарками\n"
        "• Присоединиться к существующей коробке\n"
        "• Управлять своими коробками в настройках\n\n"
        "🎁 *Выберите действие из меню ниже:*"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )