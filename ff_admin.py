import sqlite3
import json
import time
from fabric import Connection

def data_from_servers_json(server_id): #Возвращает данные по серверу под номером server_id
    with open('servers.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        try: data_server = {'ip': data[server_id]['ip'], 'login': data[server_id]['login'], 'key': data[server_id]['key']}
        except: data_server = False
    return data_server

def data_from_db(server_id): #Возвращает данные по подключению юзеров на сервере server_id
    data = False
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT user_id, port, ss_key FROM Users WHERE server_id = ?', (int(server_id),))
                data = c.fetchall()
        except: pass
    if data:
        data_users = []
        for i in data: data_users.append({'user_id': i[0], 'port': i[1], 'ss_key': i[2]})
    else:
        data_users = False
    return data_users
    
def new_connects(data_server, new_pids): #Запускает новые ss соединения на сервере. Возвращает список PIDоф процесса и юзеров
    with Connection(data_server['ip'], user=data_server['login'], connect_kwargs={'password': data_server['key']}) as conn:
        pids = []
        for new_pid in new_pids:
            conn.run('ss-server --acl /etc/shadowsocks-libev/acl/server_block_local.acl -s ' + data_server['ip'] + ' -p ' + new_pid['port'] + ' -k ' + new_pid['ss_key'] + ' -m chacha20-ietf-poly1305 -t 86400 -f ' + new_pid['pid_file'])
            pid = conn.run('cat ' + new_pid['pid_file'])
            pid = (pid.stdout.strip())
            pid = {'user_id': new_pid['user_id'], 'pid': pid}
            pids.append(pid)
    return pids

def pids_to_db(pids): #Вносит новые значения PID процессов в ДБ
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        for pid in pids:
            try:
                with connection:
                    c.execute('UPDATE Users SET pid =? WHERE user_id = ?', (int(pid['pid']), int(pid['user_id'])))
            except: pass

def renew_connects(server_id): #Объединяет все предыдущие функции. В целом запускает по новой все пропавшие SS соединения на сервере после ребута
    data_server = data_from_servers_json(server_id)
    data_users = data_from_db(server_id)
    if data_server and data_users:
        new_pids = []
        for i in data_users:
            new_pid = {'port': str(i['port']), 'ss_key': i['ss_key'], 'pid_file': str(i['user_id'])+'_'+str(i['port']), 'user_id': str(i['user_id'])}
            new_pids.append(new_pid)
        pids = new_connects(data_server, new_pids)
        pids_to_db(pids)
        result = 'SaxSexFull!'
    else:
        result = 'Something go wrong.'
        if not data_server: result = result + '\nServer does not exist.'
        if not data_users: result = result + '\nIt is no users here.'
    return result

def raw_servers_json(): #Возвращает просто содержимое файла servers.json
    with open('servers.json', 'r', encoding='utf-8') as f:
        data = f.read()
    return data

def dog_from_db(): #Собирает данные для всех юзеров с пустым балансом
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                c.execute('SELECT balance, user_id, server_id, port, pid FROM Users')
                data = c.fetchall()
        except: pass            
    time_now = int(time.time())
    disconnect_list = []
    for i in data:
        if i[2] != 0 and i[0] < time_now:
            disconnect_item = {'user_id':i[1], 'server_id':i[2], 'port':i[3], 'pid':i[4]}
            disconnect_list.append(disconnect_item)
    return disconnect_list
    
def kill_connects(data_server, disconnect_item): #Убивает процессы на сервере для юзеров с пустым балансом
    with Connection(data_server['ip'], user=data_server['login'], connect_kwargs={'password': data_server['key']}) as conn:
        pid_file = str(disconnect_item['user_id']) + '_' + str(disconnect_item['port'])
        conn.run('rm -f ' + pid_file)
        conn.run('kill ' + str(disconnect_item['pid']))

def dog_to_db(disconnected_list): #обнуляет данные в базе для юзеров с пустым балансом
    with sqlite3.connect('db.db') as connection:
        c = connection.cursor()
        try:
            with connection:
                for user_id in disconnected_list:
                    c.execute('UPDATE Users SET server_id = ?, port = ?, ss_key = ?, pid = ?, time_frst_rqst_vpn = ?, qntt_rqst_vpn =? WHERE user_id = ?', (0, 0, "", 0, 0, 0, user_id))
        except: pass

def dog(): #Объединяет предыдущие функции в одну. Разъединяет юзеров с нулевым балансом в целом
    disconnect_list = dog_from_db()
    if disconnect_list:
        disconnected_list = []
        for disconnect_item in disconnect_list:
            data_server = data_from_servers_json(str(disconnect_item['server_id']))
            kill_connects(data_server, disconnect_item)
            disconnected_list.append(disconnect_item['user_id'])
        dog_to_db(disconnected_list)
        result = "Disconnected user_ids:\n"
        for i in disconnected_list: result = result + '\n' + str(i) 
    else:
        result = 'Nobody to disconnect'
    return result
