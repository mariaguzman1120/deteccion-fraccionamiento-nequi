'''Utilidades de exploracion de datos.'''

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def build_data_overview(data: pd.DataFrame) -> pd.DataFrame:
    '''Construye un resumen general del dataset.

    Args:
        data: DataFrame con las transacciones.

    Returns:
        DataFrame con metricas generales del dataset.
    '''
    data_dict = {
        'n_transactions': len(data),
        'min_transaction_date': data.loc[:, 'transaction_date'].min(),
        'max_transaction_date': data.loc[:, 'transaction_date'].max(),
        'n_users': data.loc[:, 'user_id'].nunique(),
        'n_accounts': data.loc[:, 'account_number'].nunique(),
        'n_merchants': data.loc[:, 'merchant_id'].nunique(),
        'n_subsidiaries': data.loc[:, 'subsidiary'].nunique(),
        'duplicated_ids': data.loc[:, '_id'].duplicated().sum(),
        'non_positive_amounts': (data.loc[:, 'transaction_amount'] <= 0).sum(),
    }

    overview_df = pd.DataFrame([data_dict])

    return overview_df


def build_categorical_distribution(
    data: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    '''Construye una distribucion agregada para una columna categorica.

    Args:
        data: DataFrame con las transacciones.
        group_col: Columna usada para agrupar.

    Returns:
        DataFrame con metricas agregadas por categoria.
    '''
    distribution_df = data.groupby(group_col)

    distribution_df = distribution_df.agg(
        n_transactions=('_id', 'size'),
        total_amount=('transaction_amount', 'sum'),
        avg_amount=('transaction_amount', 'mean'),
        median_amount=('transaction_amount', 'median'),
        std_amount=('transaction_amount', 'std'),
    )

    distribution_df = distribution_df.reset_index()

    distribution_df = distribution_df.sort_values(
        'n_transactions',
        ascending=False,
    )

    distribution_df.loc[:, 'pct_transactions'] = (
        100 * distribution_df.loc[:, 'n_transactions'] / len(data)
    )

    distribution_df = distribution_df.reset_index(drop=True)

    return distribution_df


def build_amount_percentiles(
    data: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    '''Construye percentiles de monto por categoria.

    Args:
        data: DataFrame con las transacciones.
        group_col: Columna usada para agrupar.

    Returns:
        DataFrame con percentiles de `transaction_amount`.
    '''
    group_data = data.loc[:, group_col]

    amount_data = pd.to_numeric(
        data.loc[:, 'transaction_amount'],
        errors='coerce',
    )

    valid_mask = amount_data.notna()

    percentiles_df = pd.DataFrame(
        {
            group_col: group_data.loc[valid_mask],
            'transaction_amount': amount_data.loc[valid_mask],
        }
    )

    percentiles_df = percentiles_df.groupby(group_col)

    percentiles_df = percentiles_df['transaction_amount'].quantile(
        [0.01, 0.05, 0.50, 0.95, 0.99]
    )

    percentiles_df = percentiles_df.unstack()

    percentiles_df = percentiles_df.reset_index()

    percentiles_df = percentiles_df.rename(
        columns={
            0.01: 'p01',
            0.05: 'p05',
            0.50: 'p50',
            0.95: 'p95',
            0.99: 'p99',
        }
    )

    return percentiles_df


def build_daily_distribution(
    data: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    '''Construye metricas diarias por una columna categorica.

    Args:
        data: DataFrame con las transacciones.
        group_col: Columna usada para agrupar.

    Returns:
        DataFrame con metricas diarias por categoria.
    '''
    group_cols = ['transaction_day', group_col]

    daily_df = data.groupby(
        group_cols,
        as_index=False,
    )

    daily_df = daily_df.agg(
        n_transactions=('_id', 'size'),
        total_amount=('transaction_amount', 'sum'),
        avg_amount=('transaction_amount', 'mean'),
    )

    return daily_df


def build_group_distribution(
    data: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    '''Construye una distribucion agregada para varias columnas.

    Args:
        data: DataFrame con las transacciones.
        group_cols: Columnas usadas para agrupar.

    Returns:
        DataFrame con metricas y porcentajes de participacion.
    '''
    distribution_df = data.groupby(
        group_cols,
        as_index=False,
    )

    distribution_df = distribution_df.agg(
        n_transactions=('_id', 'size'),
        total_amount=('transaction_amount', 'sum'),
        avg_amount=('transaction_amount', 'mean'),
    )

    total_transactions = distribution_df.loc[:, 'n_transactions'].sum()
    total_amount = distribution_df.loc[:, 'total_amount'].sum()

    distribution_df.loc[:, 'pct_transactions'] = (
        100 * distribution_df.loc[:, 'n_transactions'] / total_transactions
    )

    distribution_df.loc[:, 'pct_total_amount'] = (
        100 * distribution_df.loc[:, 'total_amount'] / total_amount
    )

    distribution_df = distribution_df.sort_values(
        'n_transactions',
        ascending=False,
    )

    distribution_df = distribution_df.reset_index(drop=True)

    return distribution_df


def plot_daily_distribution(
    daily_df: pd.DataFrame,
    group_col: str,
    value_col: str = 'n_transactions',
) -> None:
    '''Grafica una serie diaria por categoria.

    Args:
        daily_df: DataFrame agregado por dia.
        group_col: Columna categorica usada como hue.
        value_col: Columna numerica a graficar.
    '''
    plt.figure(figsize=(18, 7))

    sns.lineplot(
        data=daily_df,
        x='transaction_day',
        y=value_col,
        hue=group_col,
    )

    plt.title(f'{value_col} por dia y {group_col}')
    plt.xlabel('Fecha')
    plt.ylabel(value_col)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def build_user_activity(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    '''Construye actividad por usuario y su resumen percentil.

    Args:
        data: DataFrame con las transacciones.

    Returns:
        Tupla con la tabla por usuario y su resumen.
    '''
    user_activity = data.groupby(
        'user_id',
        as_index=False,
    )

    user_activity = user_activity.agg(
        n_transactions=('_id', 'size'),
        n_accounts=('account_number', 'nunique'),
        total_amount=('transaction_amount', 'sum'),
        avg_amount=('transaction_amount', 'mean'),
    )

    percentile_dict = {
        'n_users': len(user_activity),
        'p50_transactions': user_activity.loc[:, 'n_transactions'].quantile(0.50),
        'p90_transactions': user_activity.loc[:, 'n_transactions'].quantile(0.90),
        'p99_transactions': user_activity.loc[:, 'n_transactions'].quantile(0.99),
        'p50_total_amount': user_activity.loc[:, 'total_amount'].quantile(0.50),
        'p90_total_amount': user_activity.loc[:, 'total_amount'].quantile(0.90),
        'p99_total_amount': user_activity.loc[:, 'total_amount'].quantile(0.99),
    }

    user_activity_summary = pd.DataFrame([percentile_dict])

    return user_activity, user_activity_summary


def plot_boxplot(
    data: pd.DataFrame,
    value_cols: list[str],
    titles: list[str],
    xlabels: list[str],
) -> None:
    '''Grafica uno o varios boxplots en una sola figura.

    Args:
        data: DataFrame con la informacion a graficar.
        value_cols: Columnas numericas a visualizar.
        titles: Titulos de cada grafico.
        xlabels: Etiquetas del eje x.
    '''
    n_plots = len(value_cols)

    fig, axes = plt.subplots(1, n_plots, figsize=(7 * n_plots, 5))

    if n_plots == 1:
        axes = [axes]

    for index, value_col in enumerate(value_cols):
        sns.boxplot(
            x=data.loc[:, value_col],
            ax=axes[index],
        )

        axes[index].set_title(titles[index])
        axes[index].set_xlabel(xlabels[index])

    plt.tight_layout()
    plt.show()
