import csv
import datetime as dt
import json
import os
import statistics
import time
from ssl import SSLError
import numpy as np
import pandas as pd
import requests

# Настройки отображения DataFrame
pd.set_option("display.max_columns", 100)

def get_request(url, parameters=None):
    """Выполняет GET-запрос и возвращает ответ в формате JSON"""
    try:
        response = requests.get(url=url, params=parameters)
    except SSLError as s:
        print('SSL Error:', s)
        for i in range(5, 0, -1):
            print('\rWaiting... ({})'.format(i), end='')
            time.sleep(1)
        print('\rRetrying.' + ' '*10)
        return get_request(url, parameters)
    
    if response:
        return response.json()
    else:
        print('No response, waiting 10 seconds...')
        time.sleep(10)
        print('Retrying.')
        return get_request(url, parameters)

def get_app_data(start, stop, parser, pause):
    """Собирает данные о приложениях с помощью указанного парсера"""
    app_data = []
    for index, row in app_list[start:stop].iterrows():
        print('Current index: {}'.format(index), end='\r')
        appid = row['appid']
        name = row['name']
        data = parser(appid, name)
        app_data.append(data)
        time.sleep(pause)  # Задержка между запросами
    return app_data

def process_batches(parser, app_list, download_path, data_filename, index_filename,
                   columns, begin=0, end=-1, batchsize=100, pause=1):
    """Обрабатывает данные партиями и сохраняет в файл"""
    print('Starting at index {}:\n'.format(begin))
    
    if end == -1:
        end = len(app_list) + 1
    
    batches = np.arange(begin, end, batchsize)
    batches = np.append(batches, end)
    
    apps_written = 0
    batch_times = []
    
    for i in range(len(batches) - 1):
        start_time = time.time()
        start = batches[i]
        stop = batches[i+1]
        
        app_data = get_app_data(start, stop, parser, pause)
        
        # Сохраняем данные в CSV
        rel_path = os.path.join(download_path, data_filename)
        with open(rel_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            
            for j in range(3, 0, -1):
                print("\rAbout to write data, don't stop script! ({})".format(j), end='')
                time.sleep(0.5)
            
            writer.writerows(app_data)
            print('\rExported lines {}-{} to {}.'.format(start, stop-1, data_filename), end=' ')
            
        apps_written += len(app_data)
        
        # Сохраняем последний обработанный индекс
        idx_path = os.path.join(download_path, index_filename)
        with open(idx_path, 'w') as f:
            print(stop, file=f)
            
        # Логирование времени выполнения
        end_time = time.time()
        time_taken = end_time - start_time
        batch_times.append(time_taken)
        mean_time = statistics.mean(batch_times)
        est_remaining = (len(batches) - i - 2) * mean_time
        
        remaining_td = dt.timedelta(seconds=round(est_remaining))
        time_td = dt.timedelta(seconds=round(time_taken))
        mean_td = dt.timedelta(seconds=round(mean_time))
        
        print('Batch {} time: {} (avg: {}, remaining: {})'.format(i, time_td, mean_td, remaining_td))
            
    print('\nProcessing batches complete. {} apps written'.format(apps_written))

def parse_steam_request(appid, name):
    """Парсер для Steam Store API"""
    url = "http://store.steampowered.com/api/appdetails/"
    parameters = {"appids": appid}
    
    json_data = get_request(url, parameters=parameters)
    json_app_data = json_data.get(str(appid), {})
    
    if json_app_data.get('success', False):
        data = json_app_data['data']
        # Обработка цены
        if 'price_overview' in data:
            price_data = data['price_overview']
            data['price_final'] = price_data.get('final', 0) / 100
            data['price_initial'] = price_data.get('initial', 0) / 100
            data['discount_percent'] = price_data.get('discount_percent', 0)
        else:
            data['price_final'] = 0
            data['price_initial'] = 0
            data['discount_percent'] = 0
        
        # Обработка даты релиза
        if 'release_date' in data:
            release_date = data['release_date'].get('date', '')
            try:
                data['release_date_parsed'] = pd.to_datetime(release_date).strftime('%Y-%m-%d')
            except:
                data['release_date_parsed'] = ''
        else:
            data['release_date_parsed'] = ''
        
        # Обработка платформ
        platforms = data.get('platforms', {})
        data['windows'] = platforms.get('windows', False)
        data['mac'] = platforms.get('mac', False)
        data['linux'] = platforms.get('linux', False)
        
        return data
    else:
        return {'name': name, 'steam_appid': appid}

def parse_steamspy_request(appid, name):
    """Парсер для SteamSpy API"""
    url = "https://steamspy.com/api.php"
    parameters = {"request": "appdetails", "appid": appid}
    
    json_data = get_request(url, parameters)
    if json_data:
        # Добавляем appid и name в данные
        json_data['appid'] = appid
        json_data['name'] = name
        return json_data
    return {'appid': appid, 'name': name}

def merge_data(steam_path, steamspy_path, output_path):
    """Объединяет данные из Steam и SteamSpy"""
    steam_df = pd.read_csv(steam_path)
    steamspy_df = pd.read_csv(steamspy_path)
    
    # Объединение данных
    merged_df = pd.merge(
        steam_df, 
        steamspy_df, 
        left_on='steam_appid', 
        right_on='appid',
        how='left'
    )
    
    # Сохранение объединенных данных
    merged_df.to_csv(output_path, index=False)
    print(f"Merged data saved to {output_path}")
    return merged_df

if __name__ == "__main__":
    # Получаем список всех приложений из SteamSpy
    url = "https://steamspy.com/api.php"
    parameters = {"request": "all"}
    json_data = get_request(url, parameters=parameters)
    steam_spy_all = pd.DataFrame.from_dict(json_data, orient='index')
    app_list = steam_spy_all[['appid', 'name']].sort_values('appid').reset_index(drop=True)
    
    # Создаем директорию для данных
    os.makedirs('data/download', exist_ok=True)
    
    # Колонки для Steam данных
    steam_columns = [
        'type', 'name', 'steam_appid', 'is_free', 'price_final', 'price_initial', 'discount_percent',
        'developers', 'publishers', 'genres', 'release_date', 'release_date_parsed',
        'windows', 'mac', 'linux', 'achievements', 'recommendations', 'metacritic',
        'controller_support', 'detailed_description', 'short_description',
        'header_image', 'website', 'support_info', 'background'
    ]
    
    # Колонки для SteamSpy данных
    steamspy_columns = [
        'appid', 'name', 'developer', 'publisher', 'score_rank', 'positive',
        'negative', 'userscore', 'owners', 'average_forever', 'average_2weeks',
        'median_forever', 'median_2weeks', 'price', 'initialprice', 'discount',
        'languages', 'genre', 'ccu', 'tags'
    ]
    
    # Сбрасываем индексы и создаем файлы
    reset_index('../data/download', 'steam_index.txt')
    reset_index('../data/download', 'steamspy_index.txt')
    
    prepare_data_file('../data/download', 'steam_app_data.csv', 0, steam_columns)
    prepare_data_file('../data/download', 'steamspy_data.csv', 0, steamspy_columns)
    
    # Получаем текущие индексы
    steam_index = get_index('../data/download', 'steam_index.txt')
    steamspy_index = get_index('../data/download', 'steamspy_index.txt')
    
    # Собираем данные из Steam Store API
    print("\n=== Сбор данных из Steam Store API ===")
    process_batches(
        parser=parse_steam_request,
        app_list=app_list,
        download_path='../data/download',
        data_filename='steam_app_data.csv',
        index_filename='steam_index.txt',
        columns=steam_columns,
        begin=steam_index,
        end=100,  # Первые 100 игр для примера
        batchsize=20,
        pause=1
    )
    
    # Собираем данные из SteamSpy API
    print("\n=== Сбор данных из SteamSpy API ===")
    process_batches(
        parser=parse_steamspy_request,
        app_list=app_list,
        download_path='../data/download',
        data_filename='steamspy_data.csv',
        index_filename='steamspy_index.txt',
        columns=steamspy_columns,
        begin=steamspy_index,
        end=100,  # Первые 100 игр для примера
        batchsize=20,
        pause=0.5
    )
    
    # Объединяем данные
    print("\n=== Объединение данных ===")
    merged_data = merge_data(
        '../data/download/steam_app_data.csv',
        '../data/download/steamspy_data.csv',
        '../data/download/merged_steam_data.csv'
    )
    
    # Выводим информацию о собранных данных
    print("\n=== Информация о собранных данных ===")
    print(f"Всего игр в SteamSpy: {len(app_list)}")
    print(f"Собрано Steam данных: {len(pd.read_csv('../data/download/steam_app_data.csv'))}")
    print(f"Собрано SteamSpy данных: {len(pd.read_csv('../data/download/steamspy_data.csv'))}")
    print(f"Объединенных записей: {len(merged_data)}")
    
    # Пример вывода первых 5 строк объединенных данных
    print("\nПервые 5 строк объединенных данных:")
    print(merged_data.head())