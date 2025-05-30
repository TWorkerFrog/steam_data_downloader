import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

def calculate_descriptive_stats(df):
    """Возвращает описательную статистику"""
    return df.describe()

def calculate_correlations(df):
    """
    Возвращает:
    - нижнеугольную матрицу корреляций
    - таблицу парных корреляций с p-value
    """
    corr_matrix = df.corr()
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    corr_matrix_masked = corr_matrix.mask(mask)

    # Считаем попарные корреляции с p-value
    pairs = []
    cols = df.columns
    for i in range(len(cols)):
        for j in range(i, len(cols)):
            x = cols[i]
            y = cols[j]
            r, p = stats.pearsonr(df[x], df[y])
            pairs.append((x, y, r, p))

    corr_df = pd.DataFrame(pairs, columns=['X', 'Y', 'Pearson r', 'p-value'])

    return corr_matrix_masked, corr_df

def run_regression_analysis(df, target_col='Среднее время игры (ч)'):
    """Выполняет множественную линейную регрессию"""
    X_cols = [col for col in df.columns if col != target_col]
    X = df[X_cols]
    X_scaled = StandardScaler().fit_transform(X)
    X_scaled = sm.add_constant(X_scaled)
    y = df[target_col]
    
    model = sm.OLS(y, X_scaled).fit()
    
    return model, X_cols
