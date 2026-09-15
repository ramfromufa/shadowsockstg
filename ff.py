import sqlite3
import json
import time
import secrets
import string
import base64
#from urllib.parse import quote
from random import randint
from fabric import Connection
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def read_servers_json(): #Возвращает массив из файла с базой серверов в формате json
    with open('servers.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return(data)

def read_texts_json(): #Возвращает массив из файла с базой текстов в формате json
    with open('texts.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return(data)
    
def read_prices_json(): #Возвращает массив из файла с базой цен и тарифов в формате json
    with open('prices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return(data)

def check_user_db(user_id, language_code): #Создаёт нового юера и возвращает language_code/ Возвращает language_code
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT language_code FROM Users WHERE user_id = ?', (user_id,))
                data = c.fetchone()
                if data:
                    language_code = data[0]
                else:
                    if language_code not in read_texts_json(): language_code = 'en'
                    c.execute('INSERT INTO Users (user_id, language_code, balance, server_id, port, ss_key, pid, time_frst_rqst_vpn, qntt_rqst_vpn) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (user_id, language_code, int(time.time()) + test_period, 0, 0, '', 0, 0, 0))
        except: pass
    return language_code

def change_language_db(user_id,language_code): #Меняет язык в db
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('UPDATE Users SET language_code = ? WHERE user_id = ?', (language_code, user_id))
        except: pass

def balance_from_db(user_id): #Возвращает данные по балансу юзера
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT balance FROM Users WHERE user_id = ?', (user_id,))
                balance = c.fetchone()
        except: pass
    balance = balance[0]
    return balance

def balance_up_db(user_id, invoice_payload): #Прибавляет к балансу юзера оплаченный пакет
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT balance FROM Users WHERE user_id = ?', (user_id,))
                balance = c.fetchone()
                balance = balance[0]
                time_now = int(time.time())
                if time_now < balance: balance = balance + int(invoice_payload)
                else: balance = time_now + int(invoice_payload)
                c.execute('UPDATE Users SET balance = ? WHERE user_id = ?', (balance, user_id))
            result = True
        except: result = False
    return result

def balance_answer(user_id, language_code): #Формирует ответ юзеру о его балансе
    texts = read_texts_json()
    balance = balance_from_db(user_id)
    if balance > int(time.time()):
        bl = time.gmtime(balance)
        balance = [bl.tm_mday,'.',bl.tm_mon,'.',bl.tm_year,' ',bl.tm_hour,':',bl.tm_min,' UTC']
        balance = ("".join(map(str,balance)))
        text = texts[language_code]['balance_text_1'] + balance + texts[language_code]['balance_text_2']
    else: text = read_texts_json()[language_code]['balance_empty_text']
    return text

def how_to_pay_list_keyboard(language_code): #Формирует клаву с выбором метода оплаты
    pay_by_stars_button = InlineKeyboardButton(
        text = read_texts_json()[language_code]['pay_by_stars_button'],
        callback_data='pay_by_stars'
    )
    pay_by_crypto_button = InlineKeyboardButton(
        text = read_texts_json()[language_code]['pay_by_crypto_button'],
        callback_data='pay_by_crypto'
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[pay_by_stars_button],
                         [pay_by_crypto_button]]
    )
    return keyboard

def stars_prices_list_keyboard(language_code):
    buttons = []
    button = {}
    prices = read_prices_json()
    for item in prices:
        button[item] = InlineKeyboardButton(
            text = prices[item][language_code] + ' ⭐ ' + str(prices[item]['coast_by_stars']),
            callback_data = 's_' + item
        )
        buttons.append([button[item]]) 
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def server_used_db(server_id): #Возвращает кортеж с server_id
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT server_id FROM Users WHERE server_id = ?', (server_id,))
                data = c.fetchall()
        except: pass
    return data

def vpn_list_keyboard(user_id):
    buttons = []
    button = {}
    servers = read_servers_json()
    for server_id in servers:
        amount = server_used_db(server_id)
        if servers[server_id]['max_amount'] > len(amount):
            button[server_id] = InlineKeyboardButton(
                text = servers[server_id]['name'],
                callback_data = server_id
            )
            buttons.append([button[server_id]]) 
    if len(buttons) > 0: keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    else: keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text = read_texts_json()[check_user_db(user_id, '')]['no_vpn'], callback_data='no_vpn')]])
    return keyboard

def user_data_db(user_id):
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT language_code, balance, server_id, port, pid, time_frst_rqst_vpn, qntt_rqst_vpn FROM Users WHERE user_id = ?', (user_id,))
                data = c.fetchone()
        except: pass
    return data

def check_ports_db(server_id):
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT port FROM Users WHERE server_id = ?', (server_id,))
                data = c.fetchall()
        except: pass
    return data

def new_user_data_db(server_id, port, ss_key, pid, time_frst_rqst_vpn, qntt_rqst_vpn, user_id): #Меняет данные юзера в db
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('UPDATE Users SET server_id = ?, port = ?, ss_key = ?, pid = ?, time_frst_rqst_vpn = ?, qntt_rqst_vpn =? WHERE user_id = ?', (server_id, port, ss_key, pid, time_frst_rqst_vpn, qntt_rqst_vpn, user_id))
        except: pass

def vpn_get(user_id, server_id): #Новое подключение
    texts = read_texts_json()
    user_data = user_data_db(user_id)
    time_now = int(time.time())
    log_new_string(time_now, user_id, 'RQST    ', user_data[1], user_data[2], user_data[3], user_data[4],'','','')
    
    if user_data[1] > time_now: #Проверка баланса перед новым подключением
        servers = read_servers_json()
        amount = server_used_db(server_id)
        if servers[server_id]['max_amount'] > len(amount): #Проверка наличия свободных подключений на сервере
            
            if (time_now - user_data[5]) > timedelta_rqst_vpn: #Проверка лимита запросов по количеству запросов в отведенный период
                qntt_rqst_vpn = 0
                time_rqst_vpn = time_now
                access = True
            elif (time_now - user_data[5]) <= timedelta_rqst_vpn and user_data[6] < max_qntt_rqst_vpn:
                qntt_rqst_vpn = user_data[6]
                time_rqst_vpn = user_data[5]
                access = True
            else: access = False
            if access:
                
                used_ports = check_ports_db(server_id)
                used_ports_list = []
                for i in used_ports: used_ports_list.append(i[0])
                while True:
                    port = randint(9000, 9999)
                    if port not in used_ports_list: break
                ss_key = ''
                alphabet = string.ascii_letters + string.digits
                for i in range(64): ss_key += ''.join(secrets.choice(alphabet))
                
                try:
                    new_pid = new_connect(servers[server_id]['ip'], servers[server_id]['login'], servers[server_id]['key'], str(port), ss_key, str(user_id)+'_'+str(port))
                    new_user_data_db(server_id, port, ss_key, new_pid, time_rqst_vpn, qntt_rqst_vpn + 1, user_id)
                    uri = generate_ss_uri({'server': servers[server_id]['ip'], 'server_port': port, 'password': ss_key, 'method': 'chacha20-ietf-poly1305'})
                    log_new_string(time_now, user_id, 'RESP    ', user_data[1], user_data[2], user_data[3], user_data[4], server_id, port,str(user_id)+'_'+str(port))
                
                    try:
                        if user_data[4] != 0: kill_connect(servers[str(user_data[2])]['ip'], servers[str(user_data[2])]['login'], servers[str(user_data[2])]['key'], str(user_id)+'_'+str(user_data[3]), str(user_data[4]))
                    except:
                        log_new_string(time_now, user_id, 'ssh_err2', user_data[1], user_data[2], user_data[3], user_data[4], server_id, port,str(user_id)+'_'+str(port))
                    message = uri
                except:
                    log_new_string(time_now, user_id, 'ssh_err1', user_data[1], user_data[2], user_data[3], user_data[4], server_id, port,str(user_id)+'_'+str(port))
                    message = texts[user_data[0]]['Something_wrong_1']
                    
            else:
                message = texts[user_data[0]]['much_rqst']
        else:
            message = texts[user_data[0]]['out_of_vpn']
    else: 
        #message = balance_answer(user_id, user_data[0])
        message = texts[user_data[0]]['out_of_balance']
    return message

def generate_ss_uri(config: dict) -> str: #Генерация ss url
    uri = f"{config['method']}:{config['password']}@{config['server']}:{config['server_port']}"
    encoded_uri = base64.b64encode(uri.encode('utf-8')).decode('utf-8')
    encoded_uri = encoded_uri[:-1]
    return f'<code>ss://{encoded_uri}</code>'

def new_connect(ip,user,key,port,ss_key,pid_file): #Запускает ss соединение на сервере. Возвращает PID процесса
    with Connection(ip, user=user, connect_kwargs={'password': key}) as conn:
        conn.run('ss-server --acl /etc/shadowsocks-libev/acl/server_block_local.acl -s ' + ip + ' -p ' + port + ' -k ' + ss_key + ' -m chacha20-ietf-poly1305 -t 86400 -f ' + pid_file)
        pid = conn.run('cat ' + pid_file)
        pid = (pid.stdout.strip())
    return pid

def kill_connect(ip,user,key,pid_file,pid): #Останавливает SS соединение на сервере
    with Connection(ip, user=user, connect_kwargs={'password': key}) as conn:
        conn.run('rm -f ' + pid_file)
        conn.run('kill '+ pid)

def manual_list_keyboard(user_id):
    # Создаем объекты инлайн-кнопок
    texts = read_texts_json()
    url_button_1 = InlineKeyboardButton(
        text = texts[check_user_db(user_id, "0")]['manual_1'],
        url = 'https://telegra.ph/Nastrojka-Shadowsocks-dlya-Android-02-23'
    )
    url_button_2 = InlineKeyboardButton(
        text = texts[check_user_db(user_id, "0")]['manual_2'],
        url = 'https://telegra.ph/Instrukciya-dlya-Outline-02-23'
    )
    # Создаем объект инлайн-клавиатуры
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[url_button_1], [url_button_2]]
    )
    return keyboard

#Функции записи логов
def log_new_string(time, usr_id, action, balance, server_id_old, port_old, pid_old, server_id_new, port, pid_file):
    with open('log.txt', 'a') as file:
        file.write(str(time)+' '+str(usr_id)+' '+action+' '+str(balance)+' '+str(server_id_old)+' '+str(port_old)+' '+str(pid_old)+' '+str(server_id_new)+' '+str(port)+' '+pid_file+'\n')

#Возвращает черный список id
def blacklist_db():
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        with connection:
                #c.execute('INSERT INTO blacklist (user_id) VALUES (1111)')
                c.execute('SELECT * FROM blacklist')
                data = c.fetchall()
    blacklist = []
    for i in data: blacklist.append(i[0])
    return blacklist

timedelta_rqst_vpn = 300           #Временной отрезок секундах, в течении которого можно сделать ограниченное количество запросов на новое подключение
max_qntt_rqst_vpn = 5              #Количество запросов на новое пдключение, доступное в определенный отрезок времени
test_period = 86400                #Тестовый период в секундах
fix_mode = True                    #Режим отладки выключен
