import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm

pd.set_option("display.max_columns", 100)
pd.set_option("display.width", 1000)

def analyze_data_v2(filename):
    df = pd.read_csv(os.path.join('data', filename))

    df = df.replace({'Оценка Metacritic': 'Н/Д', 'Steam рейтинг': 'Н/Д'}, np.nan)
    df['Steam рейтинг'] = df['Steam рейтинг'].str.replace('%', '').astype(float)
    df['Оценка Metacritic'] = pd.to_numeric(df['Оценка Metacritic'], errors='coerce')

    numeric_cols = [
        'Среднее время игры (ч)', 'Достижения', 'Цена (руб)',
        'Steam рейтинг', 'Оценка Metacritic'
    ]
    df = df[numeric_cols].dropna()

    if len(df) < 5:
        raise ValueError("Недостаточно данных для анализа")

    desc_stats = df.describe()

    corr_matrix = df.corr()

    # Сохранение расширенной матрицы корреляции
    plt.figure(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", mask=mask)
    plt.title('Попарная корреляционная матрица')
    plt.tight_layout()
    plt.savefig('data/correlation_matrix.png')
    plt.close()

    # Регрессионный анализ и графики
    os.makedirs('data/regression', exist_ok=True)
    for target in df.columns:
        for feature in df.columns:
            if target == feature:
                continue
            plt.figure(figsize=(6, 5))
            sns.regplot(x=df[feature], y=df[target], scatter_kws={'alpha': 0.6})
            plt.xlabel(feature)
            plt.ylabel(target)
            plt.title(f'{target} от {feature}')
            plt.tight_layout()
            plt.savefig(f'data/regression/{target}_vs_{feature}.png')
            plt.close()

    # Дисперсионный анализ (односторонний ANOVA)
    anova_results = {}
    for col in df.columns:
        grouped = df[col].groupby(pd.qcut(df['Среднее время игры (ч)'], q=3))
        anova_results[col] = stats.f_oneway(*[group for name, group in grouped])

    # Факторный анализ через PCA
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df)
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled_data)

    plt.figure(figsize=(8, 6))
    plt.scatter(pca_result[:, 0], pca_result[:, 1], alpha=0.7)
    plt.title('Факторный анализ (PCA, 2 компоненты)')
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('data/factor_analysis_pca.png')
    plt.close()

    # Отчёт
    with open('data/full_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== ОПИСАТЕЛЬНАЯ СТАТИСТИКА ===\n")
        f.write(desc_stats.to_string() + "\n\n")

        f.write("=== КОРРЕЛЯЦИОННЫЙ АНАЛИЗ ===\n")
        f.write("Матрица корреляции (верхний треугольник):\n")
        f.write(corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)).to_string() + "\n\n")

        f.write("=== РЕГРЕССИОННЫЙ АНАЛИЗ ===\n")
        for target in df.columns:
            for feature in df.columns:
                if target == feature:
                    continue
                slope, intercept, r, p, stderr = stats.linregress(df[feature], df[target])
                f.write(f"{target} ~ {feature}: R={r:.3f}, p={p:.4f}\n")

        f.write("\n=== ДИСПЕРСИОННЫЙ АНАЛИЗ ===\n")
        for k, result in anova_results.items():
            f.write(f"{k}: F={result.statistic:.3f}, p-value={result.pvalue:.4f}\n")

        f.write("\n=== ФАКТОРНЫЙ АНАЛИЗ (PCA) ===\n")
        f.write(f"Доля объяснённой дисперсии: {pca.explained_variance_ratio_}\n")

    print("Анализ завершён. Все результаты сохранены в папке data/")

if __name__ == "__main__":
    analyze_data_v2('steam_games_data.csv')
