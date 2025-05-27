import csv
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

class ParserError(Exception):
    pass

def get_request(url, parameters=None, max_retries=3):
    """Выполняет GET-запрос с улучшенной обработкой ошибок"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url, 
                params=parameters,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 429:
                wait_time = min(5 * (attempt + 1), 15)
                print(f"Превышен лимит запросов. Ожидание {wait_time} сек...")
                time.sleep(wait_time)
                continue
                
            if response.status_code != 200:
                print(f"Ошибка HTTP {response.status_code}. Попытка {attempt + 1}/{max_retries}")
                time.sleep(2)
                continue
                
            try:
                return response.json() if response.content else None
            except ValueError:
                print(f"Невалидный JSON. Попытка {attempt + 1}/{max_retries}")
                time.sleep(1)
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"Ошибка соединения: {e}. Попытка {attempt + 1}/{max_retries}")
            time.sleep(2)
            continue
            
    raise ParserError(f"Не удалось выполнить запрос к {url} после {max_retries} попыток")

def get_steam_app_details(appid):
    """Получает детали игры с обработкой ошибок"""
    url = "https://store.steampowered.com/api/appdetails/"
    params = {"appids": appid, "l": "russian"}
    
    try:
        data = get_request(url, params)
        if not data or not data.get(str(appid), {}).get('success'):
            return None
        return data[str(appid)]['data']
    except ParserError:
        return None

def get_steamspy_data(appid):
    """Получает данные из SteamSpy"""
    url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    try:
        return get_request(url)
    except ParserError:
        return None

def get_metacritic_score(game_name):
    """Парсит оценку с Metacritic через поиск"""
    try:
        search_url = f"https://www.metacritic.com/search/game/{game_name.replace(' ', '%20')}/results"
        response = requests.get(
            search_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if not response or response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.find('div', class_='result_wrap')
        if not first_result:
            return None
            
        score_element = first_result.find('div', class_='metascore_w')
        return int(score_element.text) if score_element else None
    except Exception as e:
        print(f"Ошибка парсинга Metacritic: {e}")
        return None

def get_steam_rating(appid):
    """Вычисляет рейтинг на основе отзывов Steam"""
    steamspy_data = get_steamspy_data(appid)
    if not steamspy_data:
        return None
        
    positive = steamspy_data.get('positive', 0)
    negative = steamspy_data.get('negative', 0)
    total = positive + negative
    
    if total == 0:
        return None
        
    return round((positive / total) * 100)

def get_game_score(appid, game_name, details):
    """Получает оценку из лучшего доступного источника"""
    # 1. Пробуем Steam API (официальные данные Metacritic)
    if details and details.get('metacritic', {}).get('score'):
        return details['metacritic']['score']
    
    # 2. Пробуем парсить Metacritic через поиск
    mc_score = get_metacritic_score(game_name)
    if mc_score:
        return mc_score
        
    # 3. Используем Steam рейтинг как fallback
    steam_rating = get_steam_rating(appid)
    return steam_rating

def parse_game_data(appid, name):
    """Парсит данные игры с улучшенным сбором оценок"""
    try:
        details = get_steam_app_details(appid)
        if not details:
            return None

        # Получаем оценку из лучшего источника
        score = get_game_score(appid, name, details)
        
        # Основные данные
        game_data = {
            'ID приложения': appid,
            'Название': name,
            'Цена (руб)': details.get('price_overview', {}).get('final', 0) / 100,
            'Бесплатная': 'Да' if details.get('is_free', False) else 'Нет',
            'Дата выхода': details.get('release_date', {}).get('date', 'Неизвестно'),
            'Оценка Metacritic': score if score is not None else 'Н/Д',
            'Рекомендации': details.get('recommendations', {}).get('total', 0),
            'Достижения': details.get('achievements', {}).get('total', 0),
            'Поддержка контроллеров': details.get('controller_support', 'Не указано'),
            'Платформы': ', '.join([k for k, v in details.get('platforms', {}).items() if v])
        }

        steamspy_data = get_steamspy_data(appid)
        if steamspy_data:
            game_data.update({
                'Положительные отзывы': steamspy_data.get('positive', 0),
                'Отрицательные отзывы': steamspy_data.get('negative', 0),
                'Среднее время игры (мин)': steamspy_data.get('average_forever', 0),
                'Медианное время игры (мин)': steamspy_data.get('median_forever', 0),
                'Steam рейтинг': f"{get_steam_rating(appid)}%" if get_steam_rating(appid) else 'Н/Д'
            })

        return game_data
    except Exception as e:
        print(f"Ошибка при обработке игры {appid}: {e}")
        return None

def get_initial_game_list():
    """Получает начальный список игр из разных категорий"""
    sources = [
        ("https://steamspy.com/api.php?request=top100in2weeks", "top"),
        ("https://steamspy.com/api.php?request=top100forever", "top_all"),
        ("https://steamspy.com/api.php?request=top100newreleases", "new"),
        ("https://steamspy.com/api.php?request=top100owned", "owned"),
        ("https://steamspy.com/api.php?request=top100action", "action"),
        ("https://steamspy.com/api.php?request=top100adventure", "adventure"),
        ("https://steamspy.com/api.php?request=top100rpg", "rpg")
    ]
    
    games = []
    for url, source_type in sources:
        try:
            data = get_request(url)
            if data:
                for appid, info in data.items():
                    games.append((appid, info))
                time.sleep(1.5)  # Задержка между категориями
        except ParserError:
            continue
            
    # Удаляем дубликаты
    seen = set()
    unique_games = []
    for appid, info in games:
        if appid not in seen:
            seen.add(appid)
            unique_games.append((appid, info))
            
    return unique_games

def collect_required_games(target_count=20):
    """Собирает ровно target_count игр с оценками"""
    games = get_initial_game_list()
    if not games:
        raise ParserError("Не удалось получить начальный список игр")
    
    result = []
    processed = 0
    
    # Перемешиваем для случайности выборки
    random.shuffle(games)
    
    for appid, info in games:
        if len(result) >= target_count:
            break
            
        processed += 1
        print(f"\nОбработка {processed}: {info['name']} (ID: {appid})")
        
        game_data = parse_game_data(appid, info['name'])
        if game_data:
            if game_data['Оценка Metacritic'] != 'Н/Д':
                result.append(game_data)
                print(f"Успешно добавлено! Оценка: {game_data['Оценка Metacritic']}")
            else:
                print("Пропуск - не удалось получить оценку")
        else:
            print("Пропуск - ошибка при обработке")
        
        time.sleep(1.5)  # Оптимальная задержка между запросами
    
    return result[:target_count]

def save_to_csv(data, filename):
    """Сохраняет данные в CSV файл"""
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\nУспешно сохранено {len(data)} игр в {filepath}")

def main():
    try:
        print("Начинаем сбор 20 игр с оценками...")
        games = collect_required_games(20)
        
        if not games:
            print("Не удалось собрать данные по играм")
            return
            
        save_to_csv(games, 'steam_games_data.csv')
        
        print("\nТоп-5 собранных игр:")
        for i, game in enumerate(games[:5], 1):
            print(f"{i}. {game['Название']} (Metacritic: {game['Оценка Metacritic']}, Steam: {game.get('Steam рейтинг', 'Н/Д')})")
            
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()