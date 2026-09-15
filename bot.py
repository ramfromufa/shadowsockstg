import ff
import ff_admin
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, BaseFilter
from aiogram.types import Message, CallbackQuery, FSInputFile, BotCommand, BotCommandScopeChat, PreCheckoutQuery
from aiogram.enums.parse_mode import ParseMode
from aiogram.utils.backoff import BackoffConfig
import os

#добавилось после того, как подключил оплату звездами
from aiogram import types

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Если токена нет, бот сразу выдаст понятную ошибку и не запустится
if not BOT_TOKEN:
    sys.exit("Ошибка: Переменная окружения BOT_TOKEN не установлена!")

# Получение строки админов из переменной окружения
admins_env = os.getenv("ADMIN_IDS", "")

# Строка в список чисел
try:
    admin_ids = [int(admin_id.strip()) for admin_id in admins_env.split(",") if admin_id.strip()]
except ValueError:
    sys.exit("Ошибка: Переменная ADMIN_IDS должна содержать только ID через запятую!")

# Проверяем, что список не пустой (опционально)
if not admin_ids:
    print("Предупреждение: Список администраторов пуст!")

# Создаем объекты бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Собственный фильтр, проверяющий юзера на черный список
class IsBlack(BaseFilter):
    def __init__(self, blacklist: list[int]) -> None:
        # В качестве параметра фильтр принимает список с целыми числами 
        self.blacklist = blacklist
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.blacklist

# Собственный фильтр, проверяющий юзера на неадмина в режиме отладки
class IsNotAdmin(BaseFilter):
    def __init__(self, admin_ids: list[int]) -> None:
        # В качестве параметра фильтр принимает список с целыми числами 
        self.admin_ids = admin_ids
    async def __call__(self, message: Message) -> bool:
        return ((message.from_user.id not in self.admin_ids) and ff.fix_mode)

# Формирование меню команд бота. функция вызывается из функции по команде /start
async def set_commands_for_chat(chat_id: int, language_code):
    texts = ff.read_texts_json()
    commands = [
        BotCommand(command = "start", description = texts[language_code]['start']),
        BotCommand(command = "vpn", description = texts[language_code]['vpn']),
        BotCommand(command = "balance", description = texts[language_code]['balance']),
        BotCommand(command = "about", description = texts[language_code]['about'])
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))

# Этот хэндлер будет срабатывать на команду "/about"
async def process_about(message: Message):
    await message.answer(
        ff.read_texts_json()[ff.check_user_db(message.from_user.id, '')]['about_text']
    )
    # Список команд админа
    if message.from_user.id in admin_ids:
        await message.answer(
            '/udb - db.db\n\n/log - log.txt\n\n/fixon - fix mode on\n\n/fixoff - fix mode off\n\n/rcnct - servers.json\n\n/dog - disconnect empty balance'
        )

# Этот хэндлер будет срабатывать на команду "/stars"
async def process_stars(message: Message):
    await message.answer(
        ff.read_texts_json()[ff.check_user_db(message.from_user.id, '')]['stars_text']
    )

# Этот хэндлер будет срабатывать на команду "/start"
async def process_start(message: Message):
    await message.answer(
        ff.read_texts_json()[ff.check_user_db(message.from_user.id, message.from_user.language_code)]['start_text']
    )
    await set_commands_for_chat(message.chat.id, ff.check_user_db(message.from_user.id, ''))

# Этот хэндлер будет срабатывать на команду "/en"
async def process_en(message: Message):
    await message.answer(
        ff.read_texts_json()['en']['start_text'],
        ff.change_language_db(message.from_user.id, 'en')
    )
    await set_commands_for_chat(message.chat.id, 'en')

# Этот хэндлер будет срабатывать на команду "/ru"
async def process_ru(message: Message):
    await message.answer(
        ff.read_texts_json()['ru']['start_text'],
        ff.change_language_db(message.from_user.id, 'ru')
    )
    await set_commands_for_chat(message.chat.id, 'ru')

# Этот хэндлер будет срабатывать на команду "/balance"
async def process_balance(message: Message):
    await message.answer(
        ff.balance_answer(message.from_user.id,ff.check_user_db(message.from_user.id, '')),
        reply_markup = ff.how_to_pay_list_keyboard(ff.check_user_db(message.from_user.id, ''))
    )

async def pay_by_stars(callback: CallbackQuery):
    await callback.message.edit_text(
        ff.read_texts_json()[ff.check_user_db(callback.from_user.id, '')]['pay_by_stars_answer'],
        parse_mode = ParseMode.HTML,
        reply_markup = ff.stars_prices_list_keyboard(ff.check_user_db(callback.from_user.id, ''))
    )
    await callback.answer()

async def pay_by_crypto(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
            ff.read_texts_json()[ff.check_user_db(callback.from_user.id, '')]['pay_by_crypto_answer'] + ff.balance_answer(callback.from_user.id, ff.check_user_db(callback.from_user.id, '')),
            reply_markup = ff.how_to_pay_list_keyboard(ff.check_user_db(callback.from_user.id, ''))
        )
    await callback.answer()

async def create_stars_invoice(callback: CallbackQuery):
    await callback.message.delete()
    
    texts = ff.read_texts_json()
    language_code = ff.check_user_db(callback.from_user.id, '')
    prices = ff.read_prices_json()
    tarif = callback.data.lstrip('s_')
    one = types.LabeledPrice(label='One item', amount=prices[tarif]['coast_by_stars'])
    
    await bot.send_invoice(
        callback.from_user.id,
        title=texts[language_code]['pay_by_stars_title'] + prices[tarif][language_code],
        description=texts[language_code]['pay_by_stars_description'] + prices[tarif][language_code + '_coast'],
        provider_token="",
        currency="XTR",
        #photo_url="https://i.postimg.cc/W12qsmLC/ticket.png",
        #photo_width=640,
        #photo_height=360,
        #photo_size=262000,
        is_flexible=False,
        prices=[one],
        start_parameter="one-more",
        payload=prices[tarif]['value']
    )
    #await callback.answer()

@dp.pre_checkout_query()
async def checkout_handler(checkout_query: PreCheckoutQuery):
    await checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def star_payment(message: Message, bot: Bot):
    if message.from_user.id in admin_ids:
        await bot.refund_star_payment(  #Возврата средств админу
            message.chat.id,
            message.successful_payment.telegram_payment_charge_id,
        )
    if ff.balance_up_db(message.from_user.id, message.successful_payment.invoice_payload):
        await message.answer(
            ff.read_texts_json()[ff.check_user_db(message.from_user.id, '')]['balance_up_answer'] + ff.balance_answer(message.from_user.id, ff.check_user_db(message.from_user.id, '')),
            reply_markup = ff.how_to_pay_list_keyboard(ff.check_user_db(message.from_user.id, ''))
        )
    else:
        await bot.refund_star_payment(  #Возврата средств
            message.chat.id,
            message.successful_payment.telegram_payment_charge_id,
        )
        await message.answer(
            ff.read_texts_json()[ff.check_user_db(message.from_user.id, '')]['balance_up_bad_answer'] + ff.balance_answer(message.from_user.id, ff.check_user_db(message.from_user.id, '')),
            reply_markup = ff.how_to_pay_list_keyboard(ff.check_user_db(message.from_user.id, ''))
        )

# Этот хэндлер будет срабатывать на команду "/vpn"
async def process_vpn(message: Message):
    await message.answer(
        ff.read_texts_json()[ff.check_user_db(message.from_user.id, '')]['vpn_list'],
        reply_markup = ff.vpn_list_keyboard(message.from_user.id)
    )

async def vpn_celect(callback: CallbackQuery):
    await callback.message.edit_text(
        ff.read_texts_json()[ff.check_user_db(callback.from_user.id, '')]['swich_off_ss'],
        reply_markup = ff.manual_list_keyboard(callback.from_user.id)
    )
    await callback.message.answer(
        ff.vpn_get(callback.from_user.id, callback.data),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

async def no_vpn(callback: CallbackQuery):
    await callback.message.edit_text(
        ff.read_texts_json()[ff.check_user_db(callback.from_user.id, '')]['no_vpn_detail']
    )
    await callback.answer()

# Этот хэндлер будет ни ченго не делать на сообщение от другого бота и на апдэйты до запуска бота.
async def skip_message(message: Message): pass
async def skip_callback_query(callback: CallbackQuery): pass

# Этот хэндлер отсылает заглушку о режиме отладки, когда он включен
async def fix_mode_message(message: Message): await message.answer('🕒 Temporarily unavailable\n🛠️ Временно недоступен')
async def fix_mode_callback_query(callback: CallbackQuery): await callback.message.answer('🕒 Temporarily unavailable\n🛠️ Временно недоступен')

# Отправление файла db.db или log.txt админу в чат с ботом. Включение/выключение fix_mode
async def send_udb(message: Message):
   if message.from_user.id in admin_ids: await bot.send_document(message.chat.id, document=FSInputFile(path='db.db'))
async def send_log(message: Message):
   if message.from_user.id in admin_ids: await bot.send_document(message.chat.id, document=FSInputFile(path='log.txt'))
#Включение и отключение режима отладки
async def send_fix_on(message: Message):
   if message.from_user.id in admin_ids:
       await message.answer('fix mode - on')
       ff.fix_mode = True
async def send_fix_off(message: Message):
   if message.from_user.id in admin_ids:
       await message.answer('fix mode - off')
       ff.fix_mode = False
#Переподключение SS соединений на сервере после его перезагрузки
async def reconnect(message: Message, command: BotCommand):
    if message.from_user.id in admin_ids:
        if command.args is None:
            await message.answer(
                ff_admin.raw_servers_json()
            )
        else:
            server_id = command.args
            server_id = str(server_id)
            await message.answer(
                ff_admin.renew_connects(server_id)
            )
#Отключить все соединения с пустым балансом
async def disconnect(message: Message):
    if message.from_user.id in admin_ids:
        await message.answer(
            ff_admin.dog()
        )

start_time = int(ff.time.time()) + 2

# Регистрируем хэндлеры
dp.message.register(skip_message, F.date.timestamp() < start_time) #Перехват апдэйтов до запуска
dp.callback_query.register(skip_callback_query, F.message.date.timestamp() < start_time) #Перехват апдэйтов до запуска
dp.message.register(skip_message, F.from_user.is_bot==True) #Перехват сообщений от ботов
dp.callback_query.register(skip_callback_query, F.from_user.is_bot==True) #Перехват сообщений от ботов
dp.message.register(skip_message, IsBlack(ff.blacklist_db())) #Единожды при запуске хэширует черный список из базы данных и далее скипает его. При изменении списка необходим перезапуск бота.
dp.callback_query.register(skip_callback_query, IsBlack(ff.blacklist_db())) #Единожды при запуске хэширует черный список из базы данных и далее сакипает его. При изменении списка необходим перезапуск бота.

dp.message.register(fix_mode_message, IsNotAdmin(admin_ids)) #Проверка на неадмина при включенном режиме отладки
dp.callback_query.register(fix_mode_callback_query, IsNotAdmin(admin_ids)) #Проверка на неадмина при включенном режиме отладки

dp.message.register(process_start, Command(commands='start'))
dp.message.register(process_en, Command(commands='en'))
dp.message.register(process_ru, Command(commands='ru'))
dp.message.register(process_balance, Command(commands='balance'))
dp.message.register(process_vpn, Command(commands='vpn'))
dp.message.register(process_about, Command(commands='about'))
dp.callback_query.register(vpn_celect, F.data.in_(ff.read_servers_json())) #Нажатие на кнопку выбора сервера.
dp.callback_query.register(no_vpn, F.data=='no_vpn') #Нажатие на кнопку "Свободных серверов нет"
dp.callback_query.register(pay_by_stars, F.data=='pay_by_stars') #Нажатие на кнопку оплаты звёздами.
dp.callback_query.register(pay_by_crypto, F.data=='pay_by_crypto') #Нажатие на кнопку оплаты криптой.
dp.callback_query.register(create_stars_invoice, F.data.lstrip('s_').in_(ff.read_prices_json())) #Нажатие на кнопку выбора тарифа с оплатой звёздами.
dp.message.register(process_stars, Command(commands='stars'))

dp.message.register(send_udb, Command(commands='udb')) #Получить bd.bd
dp.message.register(send_log, Command(commands='log')) #Получить log.txt
dp.message.register(send_fix_on, Command(commands='fixon')) #Включить режим отладки
dp.message.register(send_fix_off, Command(commands='fixoff')) #Отключить режим отладки
dp.message.register(reconnect, Command(commands='rcnct')) #Переподключение SS соединений на сервере после его перезагрузки
dp.message.register(disconnect, Command(commands='dog')) #Отключить все соединения с пустым балансом

if __name__ == '__main__':
    BACKOFF_CONFIG = BackoffConfig(min_delay=0.5, max_delay=2, factor=2, jitter=0.5)
    dp.run_polling(
        bot,
        polling_timeout = 10,
        #handle_as_tasks = True,
        backoff_config = BACKOFF_CONFIG,
        allowed_updates = ['message', 'callback_query', 'pre_checkout_query']
        #handle_signals: bool = True
    )
