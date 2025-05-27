import os
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns

# Настройки отображения
pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 1000)

def analyze_data(filename):
    """Анализирует данные и сохраняет результаты"""
    try:
        # Загрузка данных
        df = pd.read_csv(os.path.join('data', filename))
        
        # Проверка и подготовка данных
        if 'Положительные отзывы' not in df.columns or 'Отрицательные отзывы' not in df.columns:
            raise ValueError("Отсутствуют данные об отзывах")
        
        # Создаем столбец с долей положительных отзывов
        df['Всего отзывов'] = df['Положительные отзывы'] + df['Отрицательные отзывы']
        df['Доля положительных'] = df['Положительные отзывы'] / df['Всего отзывов']
        
        # Фильтрация данных
        df = df[df['Всего отзывов'] > 0]  # Игры с отзывами
        if 'Оценка Metacritic' in df.columns:
            df = df[df['Оценка Metacritic'] != 'Н/Д']  # Игры с оценкой Metacritic
            df['Оценка Metacritic'] = pd.to_numeric(df['Оценка Metacritic'], errors='coerce')
        
        # Основные анализируемые столбцы
        analysis_cols = ['Среднее время игры (мин)', 'Доля положительных']
        if 'Цена (руб)' in df.columns:
            analysis_cols.append('Цена (руб)')
        if 'Оценка Metacritic' in df.columns:
            analysis_cols.append('Оценка Metacritic')
        
        numeric_df = df[analysis_cols].apply(pd.to_numeric, errors='coerce').dropna()
        
        if len(numeric_df) < 5:
            raise ValueError("Недостаточно данных для анализа (меньше 5 игр)")
        
        # 1. Описательная статистика
        desc_stats = numeric_df.describe()
        
        # 2. Корреляционный анализ
        corr_matrix = numeric_df.corr()
        pearson_corr, pearson_p = stats.pearsonr(numeric_df['Среднее время игры (мин)'], 
                                                numeric_df['Доля положительных'])
        spearman_corr, spearman_p = stats.spearmanr(numeric_df['Среднее время игры (мин)'], 
                                                  numeric_df['Доля положительных'])
        
        # 3. Регрессионный анализ
        X_cols = [col for col in ['Доля положительных', 'Цена (руб)', 'Оценка Metacritic'] 
                 if col in numeric_df.columns]
        X = numeric_df[X_cols]
        X = StandardScaler().fit_transform(X)
        X = sm.add_constant(X)
        y = numeric_df['Среднее время игры (мин)']
        
        model = sm.OLS(y, X).fit()
        
        # Сохранение результатов
        save_results(desc_stats, corr_matrix, pearson_corr, pearson_p, 
                   spearman_corr, spearman_p, model, X_cols)
        
        # Визуализация
        create_visualizations(numeric_df, df)
        
        print("\nАнализ успешно завершен!")
        
    except Exception as e:
        print(f"\nОшибка при анализе данных: {e}")

def save_results(desc_stats, corr_matrix, pearson_corr, pearson_p, 
                spearman_corr, spearman_p, model, X_cols):
    """Сохраняет текстовые результаты анализа"""
    os.makedirs('data', exist_ok=True)
    result_path = os.path.join('data', 'analysis_results.txt')
    
    with open(result_path, 'w', encoding='utf-8') as f:
        f.write("=== ОСНОВНАЯ СТАТИСТИКА ===\n")
        f.write(desc_stats.to_string() + "\n\n")
        
        f.write("=== КОРРЕЛЯЦИОННЫЙ АНАЛИЗ ===\n")
        f.write("Матрица корреляции:\n")
        f.write(corr_matrix.to_string(float_format="%.3f") + "\n\n")
        
        f.write(f"Корреляция Пирсона (время vs рейтинг): {pearson_corr:.3f} (p-value: {pearson_p:.4f})\n")
        f.write(f"Корреляция Спирмена (время vs рейтинг): {spearman_corr:.3f} (p-value: {spearman_p:.4f})\n\n")
        
        f.write("=== РЕГРЕССИОННЫЙ АНАЛИЗ ===\n")
        f.write("Зависимая переменная: Среднее время игры (мин)\n")
        f.write("Независимые переменные:\n")
        for col in X_cols:
            f.write(f"- {col}\n")
        
        f.write("\nКоэффициенты модели:\n")
        coef_names = ['Константа'] + X_cols
        for name, coef in zip(coef_names, model.params):
            f.write(f"{name}: {coef:.3f}\n")
        
        f.write(f"\nR²: {model.rsquared:.3f} (скорректированный: {model.rsquared_adj:.3f})\n")
        f.write(f"F-статистика: {model.fvalue:.1f} (p-value: {model.f_pvalue:.4f})\n")
    
    print(f"Текстовые результаты сохранены в {result_path}")

def create_visualizations(numeric_df, full_df):
    """Создает и сохраняет графики анализа"""
    plt.figure(figsize=(16, 12))
    
    # 1. Зависимость времени от рейтинга
    plt.subplot(2, 2, 1)
    sns.regplot(x='Доля положительных', y='Среднее время игры (мин)', data=numeric_df,
                scatter_kws={'alpha': 0.6, 's': 80}, line_kws={'color': 'red'})
    plt.title('Зависимость времени игры от рейтинга', fontsize=14)
    plt.xlabel('Доля положительных отзывов', fontsize=12)
    plt.ylabel('Среднее время игры (мин)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 2. Корреляционная матрица
    plt.subplot(2, 2, 2)
    sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm', center=0,
                fmt=".2f", annot_kws={"size": 12})
    plt.title('Корреляционная матрица', fontsize=14)
    
    # 3. Распределение времени игры
    plt.subplot(2, 2, 3)
    sns.histplot(numeric_df['Среднее время игры (мин)'], bins=15, kde=True, color='skyblue')
    plt.title('Распределение времени игры', fontsize=14)
    plt.xlabel('Время игры (мин)', fontsize=12)
    plt.ylabel('Количество игр', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 4. Время игры по категориям рейтинга
    plt.subplot(2, 2, 4)
    full_df['Рейтинговая группа'] = pd.cut(full_df['Доля положительных'],
                                         bins=[0, 0.6, 0.8, 1],
                                         labels=['Низкий (<0.6)', 'Средний (0.6-0.8)', 'Высокий (>0.8)'])
    sns.boxplot(x='Рейтинговая группа', y='Среднее время игры (мин)', data=full_df,
                palette='viridis')
    plt.title('Время игры по категориям рейтинга', fontsize=14)
    plt.xlabel('Категория рейтинга', fontsize=12)
    plt.ylabel('Время игры (мин)', fontsize=12)
    plt.xticks(rotation=15)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = os.path.join('data', 'analysis_plots.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Графики сохранены в {plot_path}")

if __name__ == "__main__":
    print("Начало анализа данных...")
    analyze_data('steam_games_data.csv')