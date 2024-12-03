import os, sys, requests, time, logging
from exceptions import MissingVariables, BadRequest, ApiError
from dotenv import load_dotenv
from telebot import TeleBot
from http import HTTPStatus
from logging import StreamHandler
load_dotenv()



PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
ENV_TOKENS_LIST = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
ENV_TOKENS_NAMES = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

RESPONSE_API_KEYS = ['homeworks', 'current_date']

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка наличия необходимых перменных окружения."""
    for i in range(len(ENV_TOKENS_LIST)):
        if ENV_TOKENS_LIST[i]:
            pass
        else:
            logger.critical(
                f"Отсутствует обязательная переменная окружения:{ENV_TOKENS_NAMES[i]}"
            )



def send_message(bot, message):
    """Отправка сообщения о статусах работ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Успешная отправка сообщения -"{message}".')
    except Exception as error:
        logger.error(f'Сообщение не отправлено -"{error}".')


def get_api_answer(timestamp):
    """Запрос к endpoint'у API Домашки."""
    payload = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    if response.status_code != HTTPStatus.OK:
        logger.debug(f'Успешная отправка сообщения -"{message}".')
        raise BadRequest(f'Сервер не отвечает {response.status_code}.')
    response = response.json()
    if type(response) is not dict:
        raise ApiError('Сбой в работе API Домашки - в ответе не словарь.')
    return response

def check_response(response):
    """Проверяет ответ на соотсветсвие API Домашки."""
    if all(key in RESPONSE_API_KEYS for key in response):
        pass
    elif all(key in RESPONSE_API_KEYS for key in response):
        print(RESPONSE_API_KEYS.values())
        print('hey')
    else:
        raise ApiError('Сбой в работе API Домашки.')


def parse_status(response):
    """Извлекает статус дмашней работы."""
    if len(response['homeworks']) == 0:
        # logging.DEBUG('ЗАДАЧ НЕТ')
        return 'Изменения отсутствуют.'
    else:
        homework_name = response.get('homework_name')
        status = response.get('status')
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'



def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    # timestamp = 30*24*60*60
    while True:
        try:
            check_tokens()
            response = get_api_answer(timestamp)
            check_response(response)
            message = parse_status(response)
            # print(response['homeworks'][0])
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
