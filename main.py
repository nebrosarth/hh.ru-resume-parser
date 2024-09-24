import pandas
import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import pandas as pd
import re
# Заголовки для имитации браузера
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/112.0.0.0 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
}

# Базовый URL поиска резюме
base_search_url = 'https://hh.ru/search/resume'


# Функция для получения HTML страницы с использованием сессии
def get_page(session, url):
    try:
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Ошибка при запросе страницы {url}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Исключение при запросе страницы {url}: {e}")
        return None


# Функция для парсинга ссылок на резюме с поисковой страницы
def parse_resume_links(html):
    soup = BeautifulSoup(html, 'lxml')
    resume_links = []

    # Пример: ссылки на резюме находятся в тегах <a> с определённым классом
    # Необходимо адаптировать селекторы под текущую структуру hh.ru
    # На момент написания примера предположим, что ссылки содержат "/resume/" в href
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if '/resume/' in href:
            # Полный URL резюме
            full_url = 'https://hh.ru' + href.split('?')[0]
            if full_url not in resume_links and full_url!= "https://hh.ru/search/resume/advanced":
                resume_links.append(full_url)

    return resume_links


# Функция для парсинга текста резюме с отдельной страницы
def parse_resume(html):
    soup = BeautifulSoup(html, 'lxml')
    resume_text = ""

    try:
        # Пример: основной текст резюме может находиться в определённом контейнере
        # Необходимо адаптировать селекторы под текущую структуру hh.ru
        resume_container = soup.find('div', {'data-qa': 'resume-block'})
        if resume_container:
            resume_text = resume_container.get_text(separator='\n', strip=True)
        else:
            # Альтернативный вариант поиска
            resume_text = soup.get_text(separator='\n', strip=True)
    except Exception as e:
        print(f"Ошибка при извлечении резюме: {e}")

    return resume_text


# Функция для сохранения данных в CSV
def save_to_csv(data, filename='resumes.csv'):
    df = pd.DataFrame(data, columns=['Resume URL', 'Resume Text'])
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"Данные сохранены в {filename}")


def main():
    # Создание сессии для сохранения cookies и управления соединением
    session = requests.Session()

    all_resume_links = []
    all_resumes = []

    # Количество страниц для парсинга (например, первые 5 страниц)
    total_pages = 60

    for page in range(total_pages):
        # Формирование URL с параметрами поиска
        # Параметр 'page' начинается с 0
        params = {
            'page': page,
            # Добавьте другие параметры поиска по необходимости
        }

        # Получение HTML поисковой страницы
        print(f"Парсинг страницы поиска: {page + 1}/{total_pages}")
        search_html = get_page(session, base_search_url + '?' + '&'.join([f"{k}={v}" for k, v in params.items()]))

        if search_html:
            # Извлечение ссылок на резюме
            resume_links = parse_resume_links(search_html)
            print(f"Найдено резюме на странице {page + 1}: {len(resume_links)}")
            all_resume_links.extend(resume_links)
        else:
            print(f"Не удалось получить страницу поиска {page + 1}")

        # Случайная задержка от 1 до 3 секунд
        time.sleep(random.uniform(1, 3))

    # Удаление дубликатов ссылок
    all_resume_links = list(set(all_resume_links))
    print(f"Всего уникальных резюме для парсинга: {len(all_resume_links)}")

    columns = ['Пол', 'Возраст', 'Должность', 'Специализации', 'Занятость',
               'График работы', 'Опыт работы (лет)', 'Навыки',
               'Высшее образование', 'Знание языков',
               'Гражданство', 'Разрешение на работу', 'Желательное время в пути']
    df = pd.DataFrame(columns=columns)

    # Парсинг каждого резюме по ссылке
    for idx, resume_url in enumerate(all_resume_links, 1):
        print(f"Парсинг резюме {idx}/{len(all_resume_links)}: {resume_url}")
        resume_html = get_page(session, resume_url)
        if resume_html:
            resume_text = parse_resume(resume_html)
            text = resume_text
            data = {}

            # Функция для безопасного извлечения данных с обработкой исключений
            def safe_search(pattern, text):
                match = re.search(pattern, text)
                return match.group(1).strip() if match else None

            # Пол
            data['Пол'] = safe_search(r'(Мужчина|Женщина)', text)

            # Возраст
            data['Возраст'] = safe_search(r'(\d+)\s*лет\s,', text)

            # Должность
            data['Должность'] = safe_search(r'Резюме\s*(.+)', text)

            # Специализации
            data['Специализации'] = safe_search(r'Специализации\s*:\s*([\s\S]+?)(?=\s*Занятость)', text)

            # Занятость
            data['Занятость'] = safe_search(r'Занятость:\s*(.+?)\s*График работы', text)

            # График работы
            data['График работы'] = safe_search(r'График работы:\s*(.+?)\s*(Опыт работы|Анкета бухгалтера)', text)

            # Зарплата
            data['Зарплата'] = safe_search(r'(\d{1,3}(?:[ \ ]\d{3})*\s*[₽€$₸])', text)

            # Опыт работы (кол-во лет)
            data['Опыт работы (лет)'] = safe_search(r'(\d+)\s*год', text)

            # Навыки
            data['Навыки'] = safe_search(r'Навыки\s*\s*([\s\S]+?)(?=\s*(Высшее образование|Обо мне|Опыт вождения))', text)

            # Высшее образование
            data['Высшее образование'] = safe_search(r'Высшее образование\ss*([\s\S]+?)(?=\s*Знание языков)', text)

            # Знание языков
            data['Знание языков'] = safe_search(r'Знание языков\s*([\s\S]+?)(?=\s*(Повышение квалификации|Гражданство))', text)

            # Гражданство
            data['Гражданство'] = safe_search(r'Гражданство\s*:\s*(.+?)\s*Разрешение на работу', text)

            # Разрешение на работу
            data['Разрешение на работу'] = safe_search(r'Разрешение на работу\s*:\s*(.+?)\s*Желательное время в пути',
                                                       text)

            # Желательное время в пути
            data['Желательное время в пути'] = safe_search(r'Желательное время в пути до работы\s*:\s*(.+)', text)

            print(data)
            all_resumes.append((resume_url, resume_text))
        else:
            all_resumes.append((resume_url, "Не удалось получить содержимое резюме"))
        df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
        # Случайная задержка от 1 до 3 секунд
        time.sleep(random.uniform(1, 3))

    # Сохранение всех резюме в CSV
    df.to_csv('резюме1.csv', index=False, encoding='utf-8')


if __name__ == "__main__":
    main()