from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from database import add_participant, get_box_info, is_participant, update_participant_info, remove_participant, get_participant_info
import os
# Состояния для присоединения к коробке
(ENTER_BOX_ID, ENTER_NAME, ENTER_ADDRESS, ENTER_WISH, MENU) = range(5)

# Состояния для редактирования (начинаем с 10 для избежания конфликтов)
(EDIT_NAME, EDIT_ADDRESS, EDIT_WISH) = range(10, 13)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str = None):
    """Вспомогательная функция для показа главного меню"""
    keyboard = [
        ['Создать коробку'],
        ['Присоединиться к коробке'],
        ['Настройки']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Очищаем данные состояния
    context.user_data.clear()
    
    # Если передано специальное сообщение (например, об ошибке), показываем его
    if message:
        await update.message.reply_text(
            message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        # Иначе показываем стандартное меню
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

async def join_box(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса присоединения к коробке"""
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text(
            "⚠️ <b>Внимание!</b>\n\n"
            "Для участия в обмене подарками необходимо установить username в настройках Telegram.\n\n"
            "<b>Как это сделать:</b>\n"
            "1. Откройте настройки Telegram\n"
            "2. Перейдите в раздел «Изменить профиль»\n"
            "3. Добавьте имя пользователя (username)\n"
            "4. После установки username вернитесь и попробуйте снова",
            parse_mode='HTML'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🎄 <b>Присоединение к коробке</b>\n\n"
        "Для участия в обмене подарками введите ID коробки,\n"
        "который вам предоставил организатор.",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ENTER_BOX_ID

async def process_box_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка введенного ID коробки"""
    try:
        box_id = int(update.message.text)
        box_info = await get_box_info(box_id)
        
        if not box_info:
            await update.message.reply_text(
                "❌ Коробка с таким ID не найдена. Попробуйте еще раз:"
            )
            return ENTER_BOX_ID
        
        user_id = update.effective_user.id
        participant_exists = await is_participant(user_id, box_id)
        
        if participant_exists:
            # Если пользователь уже участник, возвращаем в главное меню
            return await show_main_menu(
                update, 
                context, 
                "❌ <b>Вы уже являетесь участником этой коробки!</b>"
            )
        
        context.user_data['joining_box_id'] = box_id
        await update.message.reply_text(
            "👤 Введите ваше имя:"
        )
        return ENTER_NAME
        
    except ValueError:
        await update.message.reply_text(
            "❌ Некорректный ID коробки. Введите число:"
        )
        return ENTER_BOX_ID

async def process_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка имени участника"""
    name = update.message.text
    context.user_data['participant_name'] = name
    
    await update.message.reply_text(
        "📍 *Отлично!*\n\n"
        "Теперь введите ваш адрес для доставки подарка:\n"
        "• Город\n"
        "• Улица, дом, квартира\n"
        "• Индекс\n"
        "• Дополнительные инструкции для курьера (при необходимости)",
        parse_mode='Markdown'
    )
    return ENTER_ADDRESS

async def process_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрботка адреса участника"""
    address = update.message.text
    context.user_data['participant_address'] = address
    
    await update.message.reply_text(
        "🎁 *Замечательно!*\n\n"
        "Последний шаг - напишите ваше пожелание для Тайного Санты:\n"
        "• Что вы хотели бы получить?\n"
        "• Есть ли у вас хобби?\n"
        "• Может быть, есть что-то, что вам точно не стоит дарить?",
        parse_mode='Markdown'
    )
    return ENTER_WISH

async def process_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка пожелания участника"""
    try:
        wish = update.message.text
        user_id = update.effective_user.id
        box_id = context.user_data.get('joining_box_id')
        name = context.user_data.get('participant_name')
        address = context.user_data.get('participant_address')

        if not all([box_id, name, address]):
            await update.message.reply_text("❌ Ошибка: не все данные были введены корректно")
            return ConversationHandler.END

        # Добавляем участника в базу данных
        await add_participant(
            user_id=user_id,
            name=name,
            address=address,
            box_id=box_id,
            wish=wish
        )

        # Показываем меню участника
        keyboard = [
            ['Вернуться в меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Получаем информацию о коробке
        box_info = await get_box_info(box_id)
        
        if box_info['box_photo'] and os.path.exists(box_info['box_photo']):
            with open(box_info['box_photo'], 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=(
                        "✅ <b>Вы успешно присоединились к коробке!</b>\n\n"
                        f"<b>Название коробки:</b> {box_info['box_name']}\n"
                        f"<b>ID коробки:</b> <code>{box_info['id_box']}</code>\n"
                        f"<b>Описание:</b>\n<blockquote>{box_info['box_desc']}</blockquote>\n\n"
                        "👤 <b>Ваши данные:</b>\n"
                        f"<b>Имя:</b> {name}\n"
                        f"<b>Адрес:</b> {address}\n"
                        f"<b>Пожелание:</b>\n<blockquote>{wish}</blockquote>\n\n"
                        "✏️ Для изменения данных, вернитесь в главное меню и перейдите в настройки"
                    ),
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
        else:
            await update.message.reply_text(
                "✅ <b>Вы успешно присоединились к коробке!</b>\n\n"
                f"<b>Название коробки:</b> {box_info['box_name']}\n"
                f"<b>ID коробки:</b> <code>{box_info['id_box']}</code>\n"
                f"<b>Описание:</b>\n<blockquote>{box_info['box_desc']}</blockquote>\n\n"
                "👤 <b>Ваши данные:</b>\n"
                f"<b>Имя:</b> {name}\n"
                f"<b>Адрес:</b> {address}\n"
                f"<b>Пожелание:</b>\n<blockquote>{wish}</blockquote>\n\n"
                "✏️ Для изменения данных, вернитесь в главное меню и перейдите в настройки",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        return MENU

    except Exception as e:
        print(f"Ошибка при добавлении участника: {e}")
        await update.message.reply_text("❌ Произошла ошиб��а при регистрации. Попробуйте снова.")
        return ConversationHandler.END

async def show_participant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, box_id: int):
    """Показать меню участника"""
    user_id = update.effective_user.id
    
    # Получаем информацию
    box_info = await get_box_info(box_id)
    user_info = await get_participant_info(user_id, box_id)
    
    if not box_info or not user_info:
        await update.message.reply_text(
            "❌ <b>Ошибка:</b> Не удалось получить информацию",
            parse_mode='HTML'
        )
        return
    
    # Показываем обновленное меню
    keyboard = [
        ['Вернуться в меню'],
        ['Изменить имя', 'Изменить адрес'],
        ['Изменить пожелание'],
        ['Информация о коробке', 'Отменить участие']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
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

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👤 <b>Редактирование имени</b>\n\n"
        "Введите новое имя:",
        parse_mode='HTML'
    )
    return EDIT_NAME

async def edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📍 <b>Редактирование адреса</b>\n\n"
        "Введите новый адрес:",
        parse_mode='HTML'
    )
    return EDIT_ADDRESS

async def edit_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🎁 <b>Редактирование пожелания</b>\n\n"
        "Введите новое пожелание:",
        parse_mode='HTML'
    )
    return EDIT_WISH

async def process_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нового имени"""
    new_name = update.message.text
    user_id = update.effective_user.id
    box_id = context.user_data.get('current_box_id')
    
    if not box_id:
        await update.message.reply_text(
            "❌ <b>Ошибка:</b> Не удалось определить коробку",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update_participant_info(user_id, box_id, 'user_name', new_name)
    await show_participant_menu(update, context, box_id)
    return MENU

async def process_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нового адреса"""
    new_address = update.message.text
    user_id = update.effective_user.id
    box_id = context.user_data.get('current_box_id')
    
    if not box_id:
        await update.message.reply_text(
            "❌ <b>Ошибка:</b> Не удалось определить коробку",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update_participant_info(user_id, box_id, 'user_adds', new_address)
    await show_participant_menu(update, context, box_id)
    return MENU

async def process_edit_wish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нового пожелания"""
    new_wish = update.message.text
    user_id = update.effective_user.id
    box_id = context.user_data.get('current_box_id')
    
    if not box_id:
        await update.message.reply_text(
            "❌ <b>Ошибка:</b> Не удалось определить коробку",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    await update_participant_info(user_id, box_id, 'user_wish', new_wish)
    await show_participant_menu(update, context, box_id)
    return MENU

async def show_box_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать информацию о коробке"""
    box_id = context.user_data.get('current_box_id')
    if not box_id:
        return await show_main_menu(
            update, 
            context, 
            "❌ <b>Ошибка:</b> Информация о коробке недоступна"
        )

    try:
        # Получаем информацию о коробке
        box_info = await get_box_info(box_id)
        user_info = await get_participant_info(update.effective_user.id, box_id)
        
        # Если есть фото, отправляем его
        if box_info['box_photo'] and os.path.exists(box_info['box_photo']):
            with open(box_info['box_photo'], 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=(
                        f"📦 Информация о коробке:\n"
                        f"ID коробки: {box_info['id_box']}\n"
                        f"Название: {box_info['box_name']}\n"
                        f"Описание: {box_info['box_desc']}\n\n"
                        f"👤 Ваши данные в коробке:\n"
                        f"Имя: {user_info['user_name']}\n"
                        f"Адрес: {user_info['user_adds']}\n"
                        f"Пожелание: {user_info['user_wish']}"
                    )
                )
        else:
            # Если фото нет, отправляем только текст
            await update.message.reply_text(
                f"📦 Информация о коробке:\n"
                f"ID коробки: {box_info['id_box']}\n"
                f"Название: {box_info['box_name']}\n"
                f"Описание: {box_info['box_desc']}\n\n"
                f"👤 Ваши данные в коробке:\n"
                f"Имя: {user_info['user_name']}\n"
                f"Адрес: {user_info['user_adds']}\n"
                f"Пожелание: {user_info['user_wish']}"
            )
        return MENU
        
    except Exception as e:
        print(f"Ошибка при получении информации о коробке: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении информации")
        return MENU

async def cancel_participation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    box_id = context.user_data.get('current_box_id')
    
    if not box_id:
        return await show_main_menu(
            update, 
            context, 
            "❌ <b>Ошибка:</b> Не удалось определить коробку"
        )
    
    await remove_participant(user_id, box_id)
    return await show_main_menu(
        update, 
        context, 
        "✅ <b>Вы успешно отменили участие в коробке</b>"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущей операции"""
    return await show_main_menu(
        update, 
        context, 
        "❌ <b>Операция отменена</b>\n\nВы вернулись в главное меню."
    )

async def return_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат в главное меню"""
    return await show_main_menu(update, context) 