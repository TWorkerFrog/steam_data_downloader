import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

def calculate_descriptive_stats(df):
    """Возвращает описательную статистику"""
    return df.describe()

def calculate_correlations(df, x_col='Среднее время игры (ч)', y_col='Доля положительных'):
    """Считает корреляции Пирсона и Спирмена + матрицу"""
    corr_matrix = df.corr()

    pearson_corr, pearson_p = stats.pearsonr(df[x_col], df[y_col])
    spearman_corr, spearman_p = stats.spearmanr(df[x_col], df[y_col])
    
    return corr_matrix, (pearson_corr, pearson_p), (spearman_corr, spearman_p)

def run_regression_analysis(df, target_col='Среднее время игры (ч)'):
    """Выполняет множественную линейную регрессию"""
    X_cols = [col for col in ['Доля положительных', 'Цена (руб)', 'Оценка Metacritic'] if col in df.columns]
    X = df[X_cols]
    X_scaled = StandardScaler().fit_transform(X)
    X_scaled = sm.add_constant(X_scaled)
    y = df[target_col]
    
    model = sm.OLS(y, X_scaled).fit()
    
    return model, X_cols
