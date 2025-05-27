import csv
import os
import time
import requests

def get_request(url, parameters=None):
    """Выполняет GET-запрос с обработкой ошибок"""
    try:
        response = requests.get(url=url, params=parameters, timeout=10)
        return response.json() if response else None
    except Exception as e:
        print(f"Ошибка запроса: {e}, повторная попытка...")
        time.sleep(5)
        return get_request(url, parameters)

def get_steam_app_details(appid):
    """Получает детальную информацию о приложении из Steam API"""
    url = "https://store.steampowered.com/api/appdetails/"
    params = {"appids": appid, "l": "russian"}
    data = get_request(url, params)
    
    if not data or not data.get(str(appid), {}).get('success'):
        return None
    
    return data[str(appid)]['data']

def parse_game_data(appid, name):
    """Извлекает ключевые данные о игре"""
    details = get_steam_app_details(appid)
    if not details:
        return None
    
    # Обработка даты релиза
    release_date = details.get('release_date', {}).get('date', '')
    if not release_date or release_date == 'Coming soon':
        release_date = 'Неизвестно'
    
    # Основные данные
    game_data = {
        'ID приложения': appid,
        'Название': name,
        'Цена (руб)': details.get('price_overview', {}).get('final', 0) / 100,
        'Бесплатная': 'Да' if details.get('is_free', False) else 'Нет',
        'Дата выхода': release_date,
        'Оценка Metacritic': details.get('metacritic', {}).get('score', 'Н/Д'),
        'Рекомендации': details.get('recommendations', {}).get('total', 0),
        'Достижения': details.get('achievements', {}).get('total', 0),
        'Поддержка контроллеров': details.get('controller_support', 'Не указано'),
        'Платформы': ', '.join([k for k, v in details.get('platforms', {}).items() if v])
    }
    
    # Дополнительные метрики из SteamSpy
    steamspy_url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    steamspy_data = get_request(steamspy_url)
    if steamspy_data:
        owners_data = steamspy_data.get('owners', '0-0')
        owners_split = owners_data.split('-')
    
        if len(owners_split) > 1:
            owners = owners_split[1]
        else:
            owners = '0'  # Значение по умолчанию, если формат неожиданный

        game_data.update({
            'Положительные отзывы': steamspy_data.get('positive', 0),
            'Отрицательные отзывы': steamspy_data.get('negative', 0),
            'Среднее время игры (мин)': steamspy_data.get('average_forever', 0),
            'Медианное время игры (мин)': steamspy_data.get('median_forever', 0),
            'Владельцы (приблизительно)': owners
        })
    
    return game_data

def save_to_csv(data, filename):
    """Сохраняет данные в CSV файл"""
    if not data:
        return
        
    os.makedirs('data', exist_ok=True)
    filepath = os.path.join('data', filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Данные сохранены в {filepath}")

def main():
    # Получаем список популярных игр (топ-50 для примера)
    steamspy_url = "https://steamspy.com/api.php?request=top100in2weeks"
    top_games = get_request(steamspy_url)
    
    if not top_games:
        print("Не удалось получить список игр")
        return
    
    # Собираем данные
    game_data = []
    for i, (appid, data) in enumerate(top_games.items()):
        if i >= 10:  # Ограничиваемся 50 играми для примера
            break
            
        print(f"Обработка игры {i+1}: {data['name']} (ID: {appid})")
        parsed_data = parse_game_data(appid, data['name'])
        if parsed_data:
            game_data.append(parsed_data)
        time.sleep(1)  # Ограничение запросов
    
    # Сохраняем сырые данные
    save_to_csv(game_data, 'steam_games_data.csv')

if __name__ == "__main__":
    main()