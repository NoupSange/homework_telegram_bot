import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telebot
from dotenv import load_dotenv

from exceptions import (СheckTokensError, InvalidJSONError, RequestApiError,
                        ResponseApiError)

load_dotenv()


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
    logging.debug('Проверка токенов...')

    TOKENS = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )
    missed_tokens = []
    for token_tuple in TOKENS:
        if token_tuple[1] is None:
            missed_tokens.append(token_tuple[0])
    if missed_tokens:
        error = f"Отсутсвуют переменные окружения:{','.join(missed_tokens)}"
        logging.critical(error)
        raise СheckTokensError(error)


def send_message(bot, message: str) -> None:
    """Отправляет сообщение о статусе работы."""
    logging.debug('Отправка сообщения...')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено.Пауза 10 мин.')
    except (
        telebot.apihelper.ApiException, requests.RequestException
    ) as error:
        logging.error(f'Сбой в работе программы: {error}')


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.debug('Выполняется запрос к API...')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except Exception as e:
        logging.error(
            f' Ошибка запроса: {e}'
        )
        raise RequestApiError(f'Ошибка запроса к api: {e}.')

    status_code = response.status_code
    if status_code != HTTPStatus.OK:
        raise ResponseApiError(
            f'Код ответа: {status_code}, причина: {response.reason}'
        )
    try:
        return response.json()

    except requests.JSONDecodeError as e:
        raise InvalidJSONError(f'Невалидный JSON - {e}')


def check_response(response: dict) -> tuple[dict, int]:
    """Проверяет ответ API на соответствие документации."""
    logging.debug("Провека ответа API на соответствие документации...")

    if not isinstance(response, dict):
        raise TypeError(f'Некорректный тип данных ответа - {type(response)}')

    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks.')

    homeworks = response['homeworks']
    current_time_timestamp = response.get('current_date', int(time.time()))
    if not isinstance(homeworks, list):
        raise TypeError('В ответе API под ключом `homeworks` данные',
                        'приходят не в виде списка.')

    return homeworks, current_time_timestamp


def parse_status(homework: dict) -> str:
    """Извлекает из конкретной домашней работы статус этой работы."""
    logging.debug("Парсинг статуса...")

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_name is None:
        raise TypeError('В ответе нет ключа homework_name')

    if homework_status is None:
        raise TypeError('В ответе нет ключа status')

    verdict = HOMEWORK_VERDICTS.get(homework['status'])

    if verdict is None:
        raise TypeError('Статус работы некорректно заполнен.')

    logging.debug(f'Новое сообщение: {verdict}')
    return (
        f'Изменился статус проверки работы "{homework_name}". {verdict}'
    )


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:

        try:
            response = (get_api_answer(timestamp))
            homeworks, current_time_timestamp = check_response(response)
            print(current_time_timestamp)
            if len(homeworks) != 0:
                homeworks = homeworks[0]
                verdict = parse_status(homeworks)
                send_message(bot, verdict)
                send_message_status = True
            else:
                send_message_status = False
                logging.debug('Изменения отсуствуют. Пауза 10 минут.')
            if send_message_status:
                timestamp = current_time_timestamp
        except Exception as e:
            logging.error(e)
            message = f'Сбой в работе программы: {e}'
            if last_message != message:
                send_message(bot, message)
                last_message = message

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[StreamHandler(stream=sys.stdout)]
    )

    main()
