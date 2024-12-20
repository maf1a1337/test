import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from database import init_app
from handler.start_handler import start
from handler.box_handler import (
    create_box,
    get_box_name,
    get_box_photo,
    skip_photo,
    get_description,
    NAME,
    PHOTO,
    DESCRIPTION
)
from handler.box_management_handler import (
    show_box_menu,
    return_to_main_menu,
    show_participants,
    download_participants,
    start_santa_draw,
    notify_participants,
    send_notification,
    delete_box_handler,
    WAITING_FOR_NOTIFICATION_TEXT,
    MANAGE_BOX
)
from handler.join_box_handler import (
    join_box, process_box_id, process_name, process_address,
    process_wish, show_participant_menu, edit_name, edit_address,
    edit_wish, show_box_info, cancel_participation, cancel,
    process_edit_name, process_edit_address, process_edit_wish,
    ENTER_BOX_ID, ENTER_NAME, ENTER_ADDRESS, ENTER_WISH,
    MENU, EDIT_NAME, EDIT_ADDRESS, EDIT_WISH
)
from handler.settings_handler import (
    show_settings,
    handle_box_callback
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # Инициализация базы данных
    init_app()
    from config.config import BOT_TOKEN
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start), group=0)
    
    # Обработчик создания коробки
    box_creation_handler = ConversationHandler(
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
    
    # Обработчик только для присоединения к коробке

    join_box_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Присоединиться к коробке$'), join_box)],
        states={
            ENTER_BOX_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_box_id)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_name)],
            ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_address)],
            ENTER_WISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_wish)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Обработчик управления коробкой
    box_management_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^Управление коробкой$'), show_box_menu),
            CallbackQueryHandler(handle_box_callback, pattern=r'^manage_box_\d+$')
        ],
        states={
            MANAGE_BOX: [
                MessageHandler(filters.Regex('^Список участников$'), show_participants),
                MessageHandler(filters.Regex('^Скачать список участников$'), download_participants),
                MessageHandler(filters.Regex('^Провести жеребьевку$'), start_santa_draw),
                MessageHandler(filters.Regex('^Уведомить участников$'), notify_participants),
                MessageHandler(filters.Regex('^Удалить коробку$'), delete_box_handler),
            ],
            WAITING_FOR_NOTIFICATION_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_notification)
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex('^Вернуться в меню$'), return_to_main_menu),
            CommandHandler('cancel', cancel)
        ],
        name="box_management",
        persistent=False
    )

    # Обработчик для меню участника после нажатия кнопки "Подробнее"
    participant_menu_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_box_callback, pattern=r'^participant_box_\d+$')],
        states={
            MENU: [
                MessageHandler(filters.Regex('^Изменить имя$'), edit_name),
                MessageHandler(filters.Regex('^Изменить адрес$'), edit_address),
                MessageHandler(filters.Regex('^Изменить пожелание$'), edit_wish),
                MessageHandler(filters.Regex('^Информация о коробке$'), show_box_info),
                MessageHandler(filters.Regex('^Отменить участие$'), cancel_participation),
            ],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_name)],
            EDIT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_address)],
            EDIT_WISH: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edit_wish)],
        },
        fallbacks=[
            MessageHandler(filters.Regex('^Вернуться в меню$'), return_to_main_menu),
            CommandHandler('cancel', cancel)
        ],
        name="participant_menu",
        persistent=False
    )

    # Добавляем обработчики в правильном порядке и без групп
    application.add_handler(box_creation_handler)
    application.add_handler(join_box_handler)
    application.add_handler(box_management_handler)
    application.add_handler(participant_menu_handler)
    
    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex('^Настройки$'), show_settings))
    application.add_handler(MessageHandler(filters.Regex('^Вернуться в меню$'), return_to_main_menu))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()