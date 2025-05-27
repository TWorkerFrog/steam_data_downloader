import os
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

# Настройки отображения
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 1000)

def analyze_data(filename):
    """Анализирует данные и сохраняет результаты"""
    df = pd.read_csv(os.path.join('data', filename))
    
    # Предварительная обработка
    df['Всего отзывов'] = df['Положительные отзывы'] + df['Отрицательные отзывы']
    df['Доля положительных'] = df['Положительные отзывы'] / df['Всего отзывов']
    df = df[df['Всего отзывов'] > 0]  # Фильтр игр без рейтинга
    
    # 1. Корреляционный анализ
    numeric_cols = ['Среднее время игры (мин)', 'Доля положительных', 'Цена (руб)', 
                   'Владельцы (приблизительно)', 'Оценка Metacritic']
    numeric_df = df[numeric_cols].apply(pd.to_numeric, errors='coerce').dropna()
    corr_matrix = numeric_df.corr()
    
    # 2. Коэффициенты корреляции
    pearson_corr, _ = stats.pearsonr(numeric_df['Среднее время игры (мин)'], 
                                    numeric_df['Доля положительных'])
    spearman_corr, _ = stats.spearmanr(numeric_df['Среднее время игры (мин)'], 
                                      numeric_df['Доля положительных'])
    
    # 3. Множественная регрессия
    X = numeric_df[['Доля положительных', 'Цена (руб)', 'Владельцы (приблизительно)', 'Оценка Metacritic']]
    X = StandardScaler().fit_transform(X)
    X = sm.add_constant(X)  # Добавляем константу
    y = numeric_df['Среднее время игры (мин)']
    
    model = sm.OLS(y, X).fit()
    
    # Сохраняем результаты анализа
    analysis_results = {
        'correlation_matrix': corr_matrix.to_dict(),
        'pearson_correlation': pearson_corr,
        'spearman_correlation': spearman_corr,
        'regression_summary': model.summary().as_text(),
        'regression_coefficients': dict(zip(
            ['Константа', 'Доля положительных', 'Цена (руб)', 
             'Владельцы (приблизительно)', 'Оценка Metacritic'], 
            model.params
        ))
    }
    
    # Сохраняем в отдельный файл
    analysis_path = os.path.join('data', 'analysis_results.txt')
    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write("=== Корреляционный анализ ===\n")
        f.write(f"Матрица корреляции:\n{corr_matrix}\n\n")
        f.write(f"Коэффициент корреляции Пирсона: {pearson_corr:.3f}\n")
        f.write(f"Коэффициент корреляции Спирмена: {spearman_corr:.3f}\n\n")
        
        f.write("=== Регрессионный анализ ===\n")
        f.write("Зависимая переменная: Среднее время игры (мин)\n")
        f.write("Независимые переменные: Доля положительных, Цена (руб), Владельцы (приблизительно), Оценка Metacritic\n\n")
        f.write(model.summary().as_text())
    
    print(f"\nРезультаты анализа сохранены в {analysis_path}")
    
    # Выводим основные выводы
    print("\n=== Основные выводы ===")
    print(f"1. Корреляция между временем в игре и рейтингом: {pearson_corr:.3f}")
    print("   Интерпретация: >0 - прямая зависимость, <0 - обратная, ~0 - нет зависимости")
    print("\n2. Результаты регрессии:")
    for name, coef in analysis_results['regression_coefficients'].items():
        print(f"   {name}: {coef:.3f}")

if __name__ == "__main__":
    analyze_data('steam_games_data.csv')