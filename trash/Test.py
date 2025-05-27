import csv
import json
import os
import time
import pandas as pd
import numpy as np
import requests
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

# Настройки отображения
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 1000)

def get_request(url, parameters=None):
    """Выполняет GET-запрос с обработкой ошибок"""
    try:
        response = requests.get(url=url, params=parameters, timeout=10)
        return response.json() if response else None
    except Exception as e:
        print(f"Request failed: {e}, retrying...")
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
    
    # Основные данные
    game_data = {
        'appid': appid,
        'name': name,
        'price': details.get('price_overview', {}).get('final', 0) / 100,
        'is_free': details.get('is_free', False),
        'release_date': details.get('release_date', {}).get('date', ''),
        'metacritic_score': details.get('metacritic', {}).get('score', 0),
        'recommendations': details.get('recommendations', {}).get('total', 0),
        'achievements': details.get('achievements', {}).get('total', 0),
        'controller_support': details.get('controller_support', ''),
        'platforms': ', '.join([k for k, v in details.get('platforms', {}).items() if v])
    }
    
    # Дополнительные метрики из SteamSpy (упрощенный запрос)
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
            'positive_ratings': steamspy_data.get('positive', 0),
            'negative_ratings': steamspy_data.get('negative', 0),
            'average_playtime': steamspy_data.get('average_forever', 0),
            'median_playtime': steamspy_data.get('median_forever', 0),
            'owners': owners
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

def analyze_data(filename):
    """Анализирует данные и сохраняет результаты"""
    df = pd.read_csv(os.path.join('data', filename))
    
    # Предварительная обработка
    df['total_ratings'] = df['positive_ratings'] + df['negative_ratings']
    df['rating_ratio'] = df['positive_ratings'] / df['total_ratings']
    df = df[df['total_ratings'] > 0]  # Фильтр игр без рейтинга
    
    # 1. Корреляционный анализ
    corr_matrix = df[['average_playtime', 'rating_ratio', 'price', 'owners', 'metacritic_score']].corr()
    
    # 2. Коэффициенты корреляции
    pearson_corr, _ = stats.pearsonr(df['average_playtime'], df['rating_ratio'])
    spearman_corr, _ = stats.spearmanr(df['average_playtime'], df['rating_ratio'])
    
    # 3. Множественная регрессия
    X = df[['rating_ratio', 'price', 'owners', 'metacritic_score']]
    X = StandardScaler().fit_transform(X)
    X = sm.add_constant(X)  # Добавляем константу
    y = df['average_playtime']
    
    model = sm.OLS(y, X).fit()
    
    # Сохраняем результаты анализа
    analysis_results = {
        'correlation_matrix': corr_matrix.to_dict(),
        'pearson_correlation': pearson_corr,
        'spearman_correlation': spearman_corr,
        'regression_summary': model.summary().as_text(),
        'regression_coefficients': dict(zip(['const', 'rating_ratio', 'price', 'owners', 'metacritic_score'], model.params))
    }
    
    # Сохраняем в отдельный файл
    analysis_path = os.path.join('data', 'analysis_results.txt')
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write("=== Корреляционный анализ ===\n")
        f.write(f"Матрица корреляции:\n{corr_matrix}\n\n")
        f.write(f"Коэффициент корреляции Пирсона: {pearson_corr:.3f}\n")
        f.write(f"Коэффициент корреляции Спирмена: {spearman_corr:.3f}\n\n")
        
        f.write("=== Регрессионный анализ ===\n")
        f.write("Зависимая переменная: average_playtime\n")
        f.write("Независимые переменные: rating_ratio, price, owners, metacritic_score\n\n")
        f.write(model.summary().as_text())
    
    print(f"\nРезультаты анализа сохранены в {analysis_path}")
    
    # Выводим основные выводы
    print("\n=== Основные выводы ===")
    print(f"1. Корреляция между временем в игре и рейтингом: {pearson_corr:.3f}")
    print("   Интерпретация: >0 - прямая зависимость, <0 - обратная, ~0 - нет зависимости")
    print("\n2. Результаты регрессии:")
    for name, coef in analysis_results['regression_coefficients'].items():
        print(f"   {name}: {coef:.3f}")

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
        if i >= 20:  # Ограничиваемся 50 играми для примера
            break
            
        print(f"Обработка игры {i+1}: {data['name']} (ID: {appid})")
        parsed_data = parse_game_data(appid, data['name'])
        if parsed_data:
            game_data.append(parsed_data)
        time.sleep(1)  # Ограничение запросов
    
    # Сохраняем сырые данные
    save_to_csv(game_data, 'steam_games_data.csv')
    
    # Анализируем данные
    analyze_data('steam_games_data.csv')

if __name__ == "__main__":
    main()