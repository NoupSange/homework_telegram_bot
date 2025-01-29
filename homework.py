import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import SendMessageError

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    logger.debug('Проверка токенов...')
    if (not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))):
        logger.critical('Отсутствуют необходимые переменные окружения')
        sys.exit()


def send_message(bot, message: str) -> None:
    """Отправляет сообщение о статусе работы."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено.Пауза 10 мин.')
    except Exception as error:
        raise SendMessageError(error)


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logger.debug('Выполняется запрос к API...')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as e:
        logger.error(
            f' Ошибка запроса: {e}'
        )
    status_code = response.status_code
    if status_code != HTTPStatus.OK:
        raise requests.RequestException(
            f'Код ответа: {status_code}, причина: {response.reason}'
        )
    try:
        return response.json()

    except requests.JSONDecodeError as e:
        raise requests.JSONDecodeError(f'Невалидный JSON - {e}')


def check_response(response: dict) -> tuple[dict, int]:
    """Проверяет ответ API на соответствие документации."""
    logger.debug("Провека ответа API на соответствие документации...")

    if not isinstance(response, dict):
        raise TypeError(f'Некорректный тип данных ответа - {type(response)}')

    homeworks = response.get('homeworks')
    current_date = response.get('current_date')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks.')

    if not isinstance(homeworks, list):
        raise TypeError('В ответе API под ключом `homeworks` данные',
                        'приходят не в виде списка.')

    if current_date is None:
        raise KeyError('Отсутствует ключ current_date.')

    if homeworks:
        homeworks = homeworks[0]

    return homeworks, current_date


def parse_status(homework: dict) -> str:
    """Извлекает из конкретной домашней работы статус этой работы."""
    logger.debug("Парсинг статуса...")

    if not homework:
        verdict = 'Изменения отсуствуют.'
        logger.debug(f'Сообщение: {verdict}')
        return verdict

    else:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')

        if homework_name is None:
            raise TypeError('В ответе нет ключа homework_name')

        if homework_status is None:
            raise TypeError('В ответе нет ключа status')

        verdict = HOMEWORK_VERDICTS.get(homework['status'])

        if verdict is None:
            raise TypeError('Статус работы некорректно заполнен.')

        logger.debug(f'Новое сообщение: {verdict}')
        return (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:

        try:
            response = (get_api_answer(timestamp))
            homework, current_time_timestamp = check_response(response)
            verdict = parse_status(homework)
            send_message(bot, verdict)
            timestamp = current_time_timestamp
        except Exception as e:
            logger.error(e)
            message = f'Сбой в работе программы: {e}'
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
