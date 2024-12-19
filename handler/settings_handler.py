from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    get_box_info, 
    get_participant_info, 
    get_user_boxes,  # Добавляем импорт
    get_created_boxes,  # Добавим получение созданных коробок
    is_participant
)
import os
from handler.join_box_handler import MENU  # Добавим импорт состояния MENU

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str = "🏠 <b>Главное меню</b>", is_callback: bool = False):
    """Вспомогательная функция для показа главного меню"""
    keyboard = [
        ['Создать коробку'],
        ['Присоединиться к коробке'],
        ['Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Очищаем данные состояния
    context.user_data.clear()
    
    if is_callback:
        await update.callback_query.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    return ConversationHandler.END

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопки Настройки"""
    user_id = update.effective_user.id
    
    # Получаем список коробок где пользователь участник
    participant_boxes = await get_user_boxes(user_id)
    
    # Получаем список коробок где пользователь организатор
    created_boxes = await get_created_boxes(user_id)
    
    if not participant_boxes and not created_boxes:
        return await show_main_menu(
            update,
            context,
            "❌ <b>У вас пока нет коробок</b>"
        )
    
    # Отправляем информацию о коробках, где пользователь участник
    if participant_boxes:
        await update.message.reply_text(
            "🎁 <b>Коробки, в которых вы участвуете:</b>",
            parse_mode='HTML'
        )
        
        for box in participant_boxes:
            keyboard = [[InlineKeyboardButton(
                "👤 Подробнее",
                callback_data=f"participant_box_{box['id_box']}"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📦 <b>{box['box_name']}</b>\n"
                f"🔢 ID: <code>{box['id_box']}</code>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    
    # Отправляем информацию о коробках, где пользователь организатор
    if created_boxes:
        await update.message.reply_text(
            "\n👑 <b>Коробки, которые вы создали:</b>",
            parse_mode='HTML'
        )
        
        for box in created_boxes:
            keyboard = [[InlineKeyboardButton(
                "⚙️ Управление",
                callback_data=f"admin_box_{box['id_box']}"
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📦 <b>{box['box_name']}</b>\n"
                f"🔢 ID: <code>{box['id_box']}</code>",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

async def handle_box_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нажатия кнопок Подробнее и Управление"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("participant_box_"):
        box_id = int(data.split('_')[-1])
        context.user_data['current_box_id'] = box_id
        
        # Получаем информацию о коробке
        box_info = await get_box_info(box_id)
        
        if not box_info:
            return await show_main_menu(
                update,
                context,
                "❌ <b>Ошибка:</b> Не удалось получить информацию о коробке",
                is_callback=True
            )
        
        # Показываем подробную информацию и меню участника
        keyboard = [
            ['Вернуться в меню'],
            ['Изменить имя', 'Изменить адрес'],
            ['Изменить пожелание'],
            ['Информация о коробке', 'Отменить участие']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Получаем информацию об участнике
        user_info = await get_participant_info(update.effective_user.id, box_id)
        
        if not user_info:
            return await show_main_menu(
                update,
                context,
                "❌ <b>Ошибка:</b> Не удалось получить информацию об участнике",
                is_callback=True
            )
        
        # Отправляем сообщение с информацией
        await query.message.reply_text(
            "🎄 <b>Информация об участии</b>\n\n"
            f"<b>Название коробки:</b> {box_info['box_name']}\n"
            f"<b>ID коробки:</b> <code>{box_info['id_box']}</code>\n"
            f"<b>Описание:</b>\n<blockquote>{box_info['box_desc']}</blockquote>\n\n"
            "👤 <b>Ваши данные:</b>\n"
            f"<b>Имя:</b> {user_info['user_name']}\n"
            f"<b>Адрес:</b> {user_info['user_adds']}\n"
            f"<b>Пожелание:</b>\n<blockquote>{user_info['user_wish']}</blockquote>\n\n"
            "✏️ Используйте кнопки ниже для управления вашими данными",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return MENU
    
    elif data.startswith("admin_box_"):
        box_id = int(data.split('_')[-1])
        context.user_data['current_box_id'] = box_id
        
        # Получаем информацию о коробке
        box_info = await get_box_info(box_id)
        
        if not box_info:
            return await show_main_menu(
                update,
                context,
                "❌ <b>Ошибка:</b> Не удалось получить информацию о коробке",
                is_callback=True
            )
        
        # Показываем меню управления коробкой
        keyboard = [
            ['Вернуться в меню'],
            ['Список участников', 'Жеребьёвка'],
            ['Изменить название', 'Изменить описание'],
            ['Изменить фото', 'Удалить коробку']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Отправляем сообщение с информацией и меню управления
        await query.message.reply_text(
            "⚙️ <b>Управление коробкой</b>\n\n"
            f"<b>Название:</b> {box_info['box_name']}\n"
            f"<b>ID коробки:</b> <code>{box_info['id_box']}</code>\n"
            f"<b>Описание:</b>\n<blockquote>{box_info['box_desc']}</blockquote>\n\n"
            "✏️ Используйте кнопки ниже для управления коробкой",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        # Если есть фото, отправляем его отдельным сообщением
        if box_info['box_photo'] and os.path.exists(box_info['box_photo']):
            with open(box_info['box_photo'], 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption="🖼 Текущее фото коробки"
                )
        
        return MENU