import csv
import io
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    delete_box, 
    get_box_participants, 
    remove_participant, 
    create_santa_pairs,
    is_box_owner,
    get_user_info,
    get_box_info
)

WAITING_FOR_NOTIFICATION_TEXT = "WAITING_FOR_NOTIFICATION_TEXT"
MANAGE_BOX = 'MANAGE_BOX'
EDIT_BOX = 'EDIT_BOX'

async def show_box_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню управления коробкой"""
    id_box = context.user_data.get('current_box_id')
    box_info = await get_box_info(id_box)
    
    keyboard = [
        [KeyboardButton("Список участников")],
        [KeyboardButton("Скачать список участников")],
        [KeyboardButton("Провести жеребьевку")],
        [KeyboardButton("Уведомить участников")],
        [KeyboardButton("Удалить коробку")],
        [KeyboardButton("Вернуться в меню")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message_text = (
        "📦 <b>Информация о коробке</b>\n\n"
        f"<b>Название:</b> {box_info['box_name']}\n"
        f"<b>ID:</b> <code>{box_info['id_box']}</code>\n"
        f"<b>Описание:</b>\n<blockquote>{box_info['box_desc']}</blockquote>\n\n"
        "⚙️ Выберите действие:"
    )
    
    if update.callback_query:
        await update.callback_query.message.reply_text(
            message_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    return MANAGE_BOX

async def return_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    keyboard = [
        ['Создать коробку'],
        ['Присоединиться к коробке'],
        ['Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🎄 <b>Главное меню Secret Santa</b>\n\n"
        "Выберите действие:\n"
        "📦 <b>Создать коробку</b> - организуйте свой обмен подарками\n"
        "🎁 <b>Присоединиться к коробке</b> - участвуйте в существующем обмене\n"
        "⚙️ <b>Настройки</b> - управляйте своими коробками",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def show_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список участников"""
    id_box = context.user_data.get('current_box_id')
    participants = await get_box_participants(id_box)
    
    if not participants:
        await update.message.reply_text("В коробке пока нет участников.")
        return
    
    message = "Список участников:\n"
    for user_id, username in participants:
        message += f"- {username}\n"
    
    await update.message.reply_text(message)

async def download_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скачать список участников в CSV"""
    id_box = context.user_data.get('current_box_id')
    participants = await get_box_participants(id_box)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Username'])
    writer.writerows(participants)
    
    output.seek(0)
    await update.message.reply_document(
        document=io.BytesIO(output.getvalue().encode()),
        filename='participants.csv'
    )

async def start_santa_draw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Провести жеребьевку"""
    user_id = update.effective_user.id
    id_box = context.user_data.get('current_box_id')
    
    if not id_box:
        await update.message.reply_text("Ошибка: коробка не выбрана")
        return
    
    if not await is_box_owner(user_id, id_box):
        await update.message.reply_text("У вас нет прав на проведение жеребьевки")
        return
    
    pairs = await create_santa_pairs(id_box)
    
    if not pairs:
        await update.message.reply_text(
            "Невозможно провести жеребьевку: недостаточно участников (минимум 2)"
        )
        return
    
    # Отправка сообщений участникам
    for santa_id, recipient_id in pairs:
        recipient = await get_user_info(recipient_id)
        try:
            await context.bot.send_message(
                chat_id=santa_id,
                text=f"🎅 Жеребьевка проведена!\n\n"
                     f"Вы стали Тайным Сантой для {recipient['username']}!"
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {santa_id}: {e}")
    
    await update.message.reply_text("✨ Жеребьевка успешно проведена! Все участники получили уведомления.")

async def notify_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить уведомление всем участникам"""
    user_id = update.effective_user.id
    id_box = context.user_data.get('current_box_id')
    
    if not await is_box_owner(user_id, id_box):
        await update.message.reply_text("У вас нет прав на отправку уведомлений")
        return
    
    await update.message.reply_text("Введите сообщение для участников:")
    return "WAITING_FOR_NOTIFICATION_TEXT"

async def send_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка уведомления всем участникам"""
    message_text = update.message.text
    id_box = context.user_data.get('current_box_id')
    participants = await get_box_participants(id_box)
    
    for user_id, _ in participants:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message_text
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
    
    await update.message.reply_text("Уведомления отправлены всем участникам!")
    return ConversationHandler.END 

async def delete_box_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление коробки"""
    user_id = update.effective_user.id
    id_box = context.user_data.get('current_box_id')
    
    if not id_box:
        await update.message.reply_text("Ошибка: коробка не выбрана")
        return await return_to_main_menu(update, context)
    
    if not await is_box_owner(user_id, id_box):
        await update.message.reply_text("У вас нет прав на удаление этой коробки")
        return await return_to_main_menu(update, context)
    
    await delete_box(id_box)
    context.user_data.pop('current_box_id', None)  # Удаляем ID коробки из контекста
    
    await update.message.reply_text(
        "Коробка успешно удалена!",
        reply_markup=ReplyKeyboardMarkup([
            ['Создать коробку'],
            ['Присоединиться к коробке'],
            ['Настройки']
        ], resize_keyboard=True)
    )
    return ConversationHandler.END 

async def handle_box_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку управления коробкой"""
    query = update.callback_query
    await query.answer()
    
    box_id = query.data.split('_')[-1]
    context.user_data['current_box_id'] = int(box_id)
    
    return await show_box_menu(update, context)