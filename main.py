import requests
from loguru import logger
import time
import json


def get_json_config(filename: str) -> dict:
    # прочитать json файл
    with open(filename) as file:
        data = json.load(file)
    return data


def update_token():
    # обновить токен в конфиге
    config = get_json_config('config.json')
    client_id = config['client_id']
    client_secret = config['client_secret']
    refresh_token = config['refresh_token']
    url = f'https://api.avito.ru/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    body = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    resp = requests.post(url, headers=headers, data=body).json()
    with open('config.json', 'w') as f:
        config['access_token'] = resp['access_token']
        config['refresh_token'] = resp['refresh_token']
        json.dump(config, f)
    logger.success('Tokens updated')


def get_headers() -> dict:
    # получить хэдеры для запроса
    config = get_json_config('config.json')
    access_token = config['access_token']
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }


def get_unread_chats(user_id):
    # получить непрочитанные сообщения
    url = f'https://api.avito.ru/messenger/v2/accounts/{user_id}/chats?unread_only=true&chat_types=u2i,u2u'
    r = requests.get(url, headers=get_headers())
    if r.status_code == 200:
        logger.success(f'Got unread chats')
        return r.json()
    else:
        logger.error('Error', r.text)
        return 0


def mark_chat_read(user_id, chat_id):
    # отметить чат прочитанным
    url = f'https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{chat_id}/read'
    r = requests.post(url, headers=get_headers())
    if r.status_code == 200:
        logger.success(f'Chat {chat_id} read')
    else:
        logger.error('Error', r.text)
    

def send_message_avito(user_id, chat_id, message: str):
    # отправить сообщение на авито
    url = f'https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages'
    body = {
        'message': {
            'text': message
        },
        'type': 'text'
    }
    r = requests.post(url, headers=get_headers(), json=body)
    if r.status_code == 200:
        logger.success(f'Sent msg to {chat_id=}')
    else:
        logger.error('Error', r.text)


def is_new_chat(user_id, chat_id):
    # если приветственное сообщение уже было отправлено
    url = f'https://api.avito.ru/messenger/v3/accounts/{user_id}/chats/{chat_id}/messages/'
    r = requests.get(url, headers=get_headers())
    if r.status_code == 200:
        response = r.json()
        for msg in response['messages']:
            if str(msg['author_id']) == str(user_id):
                return False
        return True
    else:
        return False


def main():
    msg = get_json_config('msg.json')
    welcome_message = msg['welcome_message']
    tg_channel_url = msg['tg_channel']

    config = get_json_config('config.json')
    user_id = config['user_id']

    while True:
        try:
            unread_chats = get_unread_chats(user_id)
            if not unread_chats:
                update_token()
                unread_chats = get_unread_chats(user_id)
            if unread_chats['chats']:
                for chat in unread_chats['chats']:
                    chat_id = chat['id']
                    if is_new_chat(user_id, chat_id):
                        mark_chat_read(user_id, chat_id)
                        time.sleep(1)
                        send_message_avito(user_id, chat_id, welcome_message)
                        time.sleep(1)
                        send_message_avito(user_id, chat_id, tg_channel_url)
        except Exception as e:
            logger.error(e)
        time.sleep(5)


if __name__ == '__main__':
    main()
