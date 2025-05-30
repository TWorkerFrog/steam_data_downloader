import os
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA, FactorAnalysis
import matplotlib.pyplot as plt
import seaborn as sns

from stats_utils import (
    calculate_descriptive_stats,
    calculate_correlations,
    run_regression_analysis
)

pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 1000)

def analyze_data(filename):
    try:
        df = pd.read_csv(os.path.join('data', filename))

        if 'Положительные отзывы' not in df.columns or 'Отрицательные отзывы' not in df.columns:
            raise ValueError("Отсутствуют данные об отзывах")

        df['Всего отзывов'] = df['Положительные отзывы'] + df['Отрицательные отзывы']
        df = df[df['Всего отзывов'] > 0]

        if 'Оценка Metacritic' in df.columns:
            df = df[df['Оценка Metacritic'] != 'Н/Д']
            df['Оценка Metacritic'] = pd.to_numeric(df['Оценка Metacritic'], errors='coerce')

        if 'Steam рейтинг' in df.columns:
            df = df[df['Steam рейтинг'] != 'Н/Д']
            df['Steam рейтинг'] = df['Steam рейтинг'].str.replace('%', '', regex=False).astype(float)

        analysis_cols = ['Среднее время игры (ч)']
        if 'Цена (руб)' in df.columns:
            analysis_cols.append('Цена (руб)')
        if 'Оценка Metacritic' in df.columns:
            analysis_cols.append('Оценка Metacritic')
        if 'Достижения' in df.columns:
            analysis_cols.append('Достижения')
        if 'Steam рейтинг' in df.columns:
            analysis_cols.append('Steam рейтинг')

        numeric_df = df[analysis_cols].apply(pd.to_numeric, errors='coerce').dropna()

        if len(numeric_df) < 5:
            raise ValueError("Недостаточно данных для анализа (меньше 5 игр)")

        desc_stats = calculate_descriptive_stats(numeric_df)
        corr_matrix, corr_pairs = calculate_correlations(numeric_df)
        model, X_cols = run_regression_analysis(numeric_df)

        save_results(desc_stats, corr_matrix, corr_pairs, model, X_cols)
        create_visualizations(numeric_df)

        print("\nАнализ успешно завершен!")

    except Exception as e:
        print(f"\nОшибка при анализе данных: {e}")

def save_results(desc_stats, corr_matrix, corr_pairs, model, X_cols):
    os.makedirs('data', exist_ok=True)
    result_path = os.path.join('data', 'analysis_results.txt')

    with open(result_path, 'w', encoding='utf-8') as f:
        f.write("=== ОСНОВНАЯ СТАТИСТИКА ===\n")
        f.write(desc_stats.to_string() + "\n\n")

        f.write("=== КОРРЕЛЯЦИОННЫЙ АНАЛИЗ ===\n")
        f.write("Матрица корреляции (нижний треугольник):\n")
        f.write(corr_matrix.to_string(float_format="%.3f") + "\n\n")

        f.write("Попарные корреляции (Pearson):\n")
        f.write(corr_pairs.to_string(index=False, float_format="%.3f") + "\n\n")

        f.write("=== РЕГРЕССИОННЫЙ АНАЛИЗ ===\n")
        f.write("Зависимая переменная: Среднее время игры (ч)\n")
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

def create_visualizations(numeric_df):
    plt.figure(figsize=(16, 12))

    # 1. Пример регрессии
    plt.subplot(2, 2, 1)
    if 'Оценка Metacritic' in numeric_df.columns:
        sns.regplot(x='Оценка Metacritic', y='Среднее время игры (ч)', data=numeric_df,
                    scatter_kws={'alpha': 0.6, 's': 80}, line_kws={'color': 'red'})
        plt.title('Время игры от Metacritic', fontsize=14)
        plt.xlabel('Оценка Metacritic')
        plt.ylabel('Среднее время игры (ч)')
        plt.grid(True, alpha=0.3)

    # 2. Корреляционная матрица (нижний треугольник)
    plt.subplot(2, 2, 2)
    corr_matrix = numeric_df.corr()
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(corr_matrix, mask=mask, annot=True, cmap='coolwarm', center=0,
                fmt=".2f", annot_kws={"size": 12}, square=True)
    plt.title('Корреляционная матрица (нижний треугольник)', fontsize=14)

    # 3. Распределение времени игры
    plt.subplot(2, 2, 3)
    sns.histplot(numeric_df['Среднее время игры (ч)'], bins=15, kde=True, color='skyblue')
    plt.title('Распределение времени игры', fontsize=14)
    plt.xlabel('Время игры (ч)')
    plt.ylabel('Количество игр')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = os.path.join('data', 'analysis_plots.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Графики сохранены в {plot_path}")

    # Парные регрессии
    pairs = [
        ('Среднее время игры (ч)', 'Достижения'),
        ('Среднее время игры (ч)', 'Цена (руб)'),
        ('Среднее время игры (ч)', 'Оценка Metacritic'),
        ('Среднее время игры (ч)', 'Steam рейтинг')
    ]
    for y, x in pairs:
        if x in numeric_df.columns and y in numeric_df.columns:
            plt.figure(figsize=(6, 5))
            sns.regplot(x=x, y=y, data=numeric_df,
                        scatter_kws={'alpha': 0.6}, line_kws={'color': 'red'})
            plt.title(f'Регрессия: {y} от {x}')
            plt.grid(True, alpha=0.3)
            plot_name = f"regression_{x}_vs_{y}.png".replace(' ', '_')
            plt.savefig(os.path.join('data', plot_name), dpi=300, bbox_inches='tight')
            plt.close()

    # PCA
    try:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_df)
        pca = PCA(n_components=2)
        components = pca.fit_transform(scaled_data)

        plt.figure(figsize=(6, 5))
        plt.scatter(components[:, 0], components[:, 1], alpha=0.7)
        plt.title('PCA: Снижение размерности до 2D')
        plt.xlabel('PC1')
        plt.ylabel('PC2')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join('data', 'pca_plot.png'), dpi=300)
        plt.close()
    except Exception as e:
        print(f"PCA ошибка: {e}")

    # Факторный анализ
    try:
        fa = FactorAnalysis(n_components=2, random_state=0)
        fa_components = fa.fit_transform(scaled_data)

        plt.figure(figsize=(6, 5))
        plt.scatter(fa_components[:, 0], fa_components[:, 1], alpha=0.7, color='orange')
        plt.title('Факторный анализ: 2 фактора')
        plt.xlabel('Фактор 1')
        plt.ylabel('Фактор 2')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join('data', 'factor_analysis_plot.png'), dpi=300)
        plt.close()
    except Exception as e:
        print(f"Factor Analysis ошибка: {e}")

if __name__ == "__main__":
    print("Начало анализа данных...")
    analyze_data('steam_games_data.csv')
