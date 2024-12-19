from database import add_box
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from .box_management_handler import (
    show_box_menu,
    return_to_main_menu,
    show_participants,
    download_participants,
    start_santa_draw,
    notify_participants,
    send_notification
)
import os
from datetime import datetime

# Определяем состояния
NAME, PHOTO, DESCRIPTION = range(3)
WAITING_FOR_NOTIFICATION_TEXT = "WAITING_FOR_NOTIFICATION_TEXT"

# Создаем константу для пути к папке с фотографиями
PHOTO_DIR = "photo_box"

# Создаем папку, если её нет
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

async def create_box(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания коробки"""
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text(
            "⚠️ <b>Внимание!</b>\n\n"
            "Для создания коробки необходимо установить username в настройках Telegram.\n\n"
            "<b>Как это сделать:</b>\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел «Изменить профиль»\n"
            "3. Добавьте имя пользователя (username)\n"
            "4. После установки username вернитесь и попробуйте снова",
            parse_mode='HTML'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🎁 *Создание новой коробки*\n\n"
        "Давайте создадим уютное место для обмена подарками!\n\n"
        "✏️ Пожалуйста, введите название коробки:",
        parse_mode='Markdown'
    )
    return NAME

async def get_box_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия коробки"""
    box_name = update.message.text
    if len(box_name) > 100:
        await update.message.reply_text(
            "❌ *Ошибка:* Название слишком длинное!\n"
            f"Максимальная длина: 100 символов\n"
            f"Текущая длина: {len(box_name)} символов",
            parse_mode='Markdown'
        )
        return NAME
    
    context.user_data['box_name'] = box_name
    await update.message.reply_text(
        "📸 *Отлично!* Теперь добавьте фотографию для вашей коробки\n"
        "(или используйте /skip, чтобы пропустить этот шаг)",
        parse_mode='Markdown'
    )
    return PHOTO

async def get_box_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем фото коробки"""
    photo_file = await update.message.photo[-1].get_file()
    
    # Создаем уникальное имя файла используя timestamp
    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{update.effective_user.id}.jpg"
    file_path = os.path.join(PHOTO_DIR, file_name)
    
    # Скачиваем и сохраняем фото
    await photo_file.download_to_drive(file_path)
    
    # Сохраняем путь к фото в контексте
    context.user_data['box_photo'] = file_path
    
    await update.message.reply_text(
        "Фото успешно сохранено! Теперь введите описание коробки:"
    )
    return DESCRIPTION

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск добавления фото"""
    context.user_data['box_photo'] = None
    await update.message.reply_text(
        "📝 *Хорошо!* Фото пропущено.\n\n"
        "Теперь добавьте описание коробки:\n"
        "• Укажите тематику подарков\n"
        "• Добавьте ограничения по стоимости\n"
        "• Укажите дату проведения",
        parse_mode='Markdown'
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершаем создание коробки"""
    description = update.message.text
    
    if len(description) > 200:
        await update.message.reply_text(
            "Описание слишком длинное! Пожалуйста, сократите его до 200 символов.\n"
            f"Текущая длина: {len(description)} символов"
        )
        return DESCRIPTION
    
    context.user_data['box_description'] = description
    user_id = update.effective_user.id
    
    # Сохраняем в базу данных и получаем id созданной коробки
    box_id = await add_box(
        user_id=user_id,
        box_name=context.user_data['box_name'],
        box_photo=context.user_data['box_photo'],
        box_desc=context.user_data['box_description']
    )
    
    # Сохраняем id коробки в context.user_data
    context.user_data['current_box_id'] = box_id
    
    # Показываем меню управления коробкой
    keyboard = [
        ['Вернуться в меню'],
        ['Список участников', 'Удалить участника'],
        ['Провести жеребьевку', 'Уведомить участников'],
        ['Удалить коробку', 'Скачать список участников']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Отправляем сообщение с фото
    if context.user_data['box_photo'] and os.path.exists(context.user_data['box_photo']):
        with open(context.user_data['box_photo'], 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=(
                    "✅ <b>Коробка успешно создана!</b>\n\n"
                    f"<b>Название:</b> {context.user_data['box_name']}\n"
                    f"<b>ID коробки:</b> <code>{box_id}</code>\n"
                    f"<b>Описание:</b>\n<blockquote>{context.user_data['box_description']}</blockquote>\n\n"
                    "🎯 <b>Доступные действия:</b>\n"
                    "• Управление участниками\n"
                    "• Проведение жеребьевки\n"
                    "• Отправка уведомлений"
                ),
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text(
            "✅ <b>Коробка успешно создана!</b>\n\n"
            f"<b>Название:</b> {context.user_data['box_name']}\n"
            f"<b>ID коробки:</b> <code>{box_id}</code>\n"
            f"<b>Описание:</b>\n<blockquote>{context.user_data['box_description']}</blockquote>\n\n"
            "🎯 <b>Доступные действия:</b>\n"
            "• Управление участниками\n"
            "• Проведение жеребьевки\n"
            "• Отправка уведомлений",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    return ConversationHandler.END

# Добавьте этот обработчик в основной файл
box_conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Создать коробку$'), create_box)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_box_name)],
        PHOTO: [
            MessageHandler(filters.PHOTO, get_box_photo),
            CommandHandler('skip', skip_photo)
        ],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
    },
    fallbacks=[]
)

box_management_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('^Управление коробкой$'), show_box_menu)],
    states={
        WAITING_FOR_NOTIFICATION_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_notification)
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex('^Вернуться в меню$'), return_to_main_menu),
        MessageHandler(filters.Regex('^Список участников$'), show_participants),
        MessageHandler(filters.Regex('^Скачать список участников$'), download_participants),
        MessageHandler(filters.Regex('^Провести жеребьевку$'), start_santa_draw),
        MessageHandler(filters.Regex('^Уведомить участников$'), notify_participants),
    ]
)