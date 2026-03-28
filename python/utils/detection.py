"""Utilidades para construir un flujo de deteccion heuristica."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

DEFAULT_ENTITY_COLS = ['user_id', 'account_number', 'transaction_type']


def _build_unique_cols(columns: list[str]) -> list[str]:
    """Elimina columnas repetidas conservando el orden original."""
    return list(dict.fromkeys(columns))


def _resolve_entity_cols(entity_cols: list[str] | None) -> list[str]:
    """Devuelve la unidad analitica por defecto del detector."""
    if entity_cols is None:
        return DEFAULT_ENTITY_COLS

    return entity_cols


def build_window_features(
    data: pd.DataFrame,
    entity_cols: list[str] | None = None,
    window: str = '24h',
) -> pd.DataFrame:
    """Construye features de ventana movil para la entidad analizada.

    Args:
        data: DataFrame de transacciones limpio.
        entity_cols: Columnas que definen la entidad de analisis.
        window: Tamano de la ventana movil.

    Returns:
        DataFrame con metricas agregadas por ventana.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    required_cols = [
        *entity_cols,
        '_id',
        'transaction_date',
        'transaction_day',
        'transaction_amount',
    ]

    window_data = data.loc[:, required_cols]

    sort_cols = [*entity_cols, 'transaction_date']
    window_data = window_data.sort_values(sort_cols)

    rolling_df = window_data.groupby(entity_cols).rolling(
        window,
        on='transaction_date',
    )

    window_features = rolling_df['transaction_amount'].agg(
        ['count', 'sum', 'mean', 'std']
    )

    window_features = window_features.reset_index()
    window_features['cv'] = (
        window_features['std'] / window_features['mean']
    )
    window_features['transaction_day'] = (
        window_features['transaction_date'].dt.date
    )

    return window_features


def build_window_feature_distribution(
    window_features: pd.DataFrame,
    value_cols: list[str] | None = None,
    quantiles: list[float] | None = None,
) -> pd.DataFrame:
    """Resume la distribucion de features de ventana por percentiles.

    Args:
        window_features: DataFrame con features de ventana.
        value_cols: Columnas numericas a resumir.
        quantiles: Lista de percentiles a calcular.

    Returns:
        DataFrame con percentiles por feature.
    """
    if value_cols is None:
        value_cols = ['count', 'sum', 'cv']

    if quantiles is None:
        quantiles = [0.01, 0.05, 0.50, 0.95, 0.99]

    distribution_df = window_features.loc[:, value_cols]
    distribution_df = distribution_df.quantile(quantiles)
    distribution_df = distribution_df.T
    distribution_df = distribution_df.reset_index()

    rename_map = {'index': 'feature'}

    for quantile in quantiles:
        quantile_label = int(100 * quantile)
        rename_map[quantile] = f'p{quantile_label:02d}'

    distribution_df = distribution_df.rename(columns=rename_map)

    return distribution_df


def plot_window_feature_distribution(
    window_features: pd.DataFrame,
    value_cols: list[str] | None = None,
    bins: int = 50,
) -> None:
    """Grafica la distribucion de features de ventana.

    Args:
        window_features: DataFrame con features de ventana.
        value_cols: Columnas numericas a graficar.
        bins: Numero de bins del histograma.
    """
    if value_cols is None:
        value_cols = ['count', 'sum', 'cv']

    plot_df = window_features.loc[:, value_cols]

    if 'cv' in value_cols:
        plot_df = plot_df.dropna(subset=['cv'])

    n_plots = len(value_cols)

    fig, axes = plt.subplots(1, n_plots, figsize=(6 * n_plots, 5))

    if n_plots == 1:
        axes = [axes]

    for index, value_col in enumerate(value_cols):
        sns.histplot(
            plot_df.loc[:, value_col],
            bins=bins,
            ax=axes[index],
        )

        axes[index].set_title(f'Distribucion de {value_col}')
        axes[index].set_xlabel(value_col)

    plt.tight_layout()
    plt.show()


def build_daily_window_alerts(
    window_features: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Selecciona la ultima ventana observada por dia.

    Args:
        window_features: Features de ventana movil.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame con una fila por entidad y dia.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    group_cols = [*entity_cols, 'transaction_day']

    last_idx = window_features.groupby(group_cols)['transaction_date'].idxmax()

    alerts = window_features.loc[last_idx]
    alerts = alerts.reset_index(drop=True)

    return alerts


def build_daily_baseline_features(
    data: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Construye una referencia diaria del periodo observado y z-scores.

    Args:
        data: DataFrame de transacciones limpio.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame diario con metricas y desviaciones respecto a la
        referencia del periodo observado.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    group_cols = [*entity_cols, 'transaction_day']

    baseline_df = data.groupby(
        group_cols,
        as_index=False,
    )

    baseline_df = baseline_df.agg(
        day_tx_count=('_id', 'size'),
        day_amount=('transaction_amount', 'sum'),
    )

    baseline_df['user_avg_day_tx'] = (
        baseline_df.groupby(entity_cols)['day_tx_count'].transform('mean')
    )

    baseline_df['user_std_day_tx'] = (
        baseline_df.groupby(entity_cols)['day_tx_count'].transform('std')
    )

    baseline_df['user_avg_day_amount'] = (
        baseline_df.groupby(entity_cols)['day_amount'].transform('mean')
    )

    baseline_df['user_std_day_amount'] = (
        baseline_df.groupby(entity_cols)['day_amount'].transform('std')
    )

    baseline_df['z_day_tx_count'] = (
        baseline_df['day_tx_count'] - baseline_df['user_avg_day_tx']
    ) / baseline_df['user_std_day_tx']

    baseline_df['z_day_amount'] = (
        baseline_df['day_amount'] - baseline_df['user_avg_day_amount']
    ) / baseline_df['user_std_day_amount']

    return baseline_df


def build_daily_destination_features(
    data: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Construye features diarias de cuenta y destino observable.

    Args:
        data: DataFrame de transacciones limpio.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame diario con contexto de `account_number`, `merchant_id`
        y `subsidiary`.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    group_cols = _build_unique_cols([*entity_cols, 'transaction_day'])

    merchant_group_cols = _build_unique_cols([*group_cols, 'merchant_id'])

    merchant_df = data.groupby(
        merchant_group_cols,
        as_index=False,
    )

    merchant_df = merchant_df.agg(
        merchant_tx_count=('_id', 'size'),
        merchant_amount=('transaction_amount', 'sum'),
        merchant_n_subsidiaries=('subsidiary', 'nunique'),
    )

    merchant_df['merchant_tx_share'] = (
        merchant_df['merchant_tx_count']
        / merchant_df.groupby(group_cols)['merchant_tx_count'].transform('sum')
    )

    merchant_df['merchant_amount_share'] = (
        merchant_df['merchant_amount']
        / merchant_df.groupby(group_cols)['merchant_amount'].transform('sum')
    )

    merchant_summary = merchant_df.groupby(
        group_cols,
        as_index=False,
    )

    merchant_summary = merchant_summary.agg(
        top_merchant_tx_share=('merchant_tx_share', 'max'),
        top_merchant_amount_share=('merchant_amount_share', 'max'),
        n_unique_merchants=('merchant_id', 'nunique'),
        max_subsidiaries_per_merchant=('merchant_n_subsidiaries', 'max'),
    )

    merchant_top_idx = merchant_df.groupby(group_cols)['merchant_tx_count'].idxmax()

    merchant_top_df = merchant_df.loc[
        merchant_top_idx,
        _build_unique_cols(
            [
            *group_cols,
            'merchant_id',
            'merchant_tx_count',
            'merchant_amount',
            'merchant_n_subsidiaries',
            ]
        ),
    ]

    merchant_top_df = merchant_top_df.reset_index(drop=True)
    merchant_top_df['top_merchant_id'] = merchant_top_df['merchant_id']
    merchant_top_df['top_merchant_tx_count'] = merchant_top_df['merchant_tx_count']
    merchant_top_df['top_merchant_amount'] = merchant_top_df['merchant_amount']
    merchant_top_df['top_merchant_n_subsidiaries'] = (
        merchant_top_df['merchant_n_subsidiaries']
    )

    merchant_top_df = merchant_top_df.loc[
        :,
        [
            *group_cols,
            'top_merchant_id',
            'top_merchant_tx_count',
            'top_merchant_amount',
            'top_merchant_n_subsidiaries',
        ],
    ]

    subsidiary_group_cols = _build_unique_cols([*group_cols, 'subsidiary'])

    subsidiary_df = data.groupby(
        subsidiary_group_cols,
        as_index=False,
    )

    subsidiary_df = subsidiary_df.agg(
        subsidiary_tx_count=('_id', 'size'),
        subsidiary_amount=('transaction_amount', 'sum'),
    )

    subsidiary_df['subsidiary_tx_share'] = (
        subsidiary_df['subsidiary_tx_count']
        / subsidiary_df.groupby(group_cols)['subsidiary_tx_count'].transform('sum')
    )

    subsidiary_df['subsidiary_amount_share'] = (
        subsidiary_df['subsidiary_amount']
        / subsidiary_df.groupby(group_cols)['subsidiary_amount'].transform('sum')
    )

    subsidiary_summary = subsidiary_df.groupby(
        group_cols,
        as_index=False,
    )

    subsidiary_summary = subsidiary_summary.agg(
        top_subsidiary_tx_share=('subsidiary_tx_share', 'max'),
        top_subsidiary_amount_share=('subsidiary_amount_share', 'max'),
        n_unique_subsidiaries=('subsidiary', 'nunique'),
    )

    subsidiary_top_idx = subsidiary_df.groupby(group_cols)['subsidiary_tx_count'].idxmax()

    subsidiary_top_df = subsidiary_df.loc[
        subsidiary_top_idx,
        _build_unique_cols(
            [
            *group_cols,
            'subsidiary',
            'subsidiary_tx_count',
            'subsidiary_amount',
            ]
        ),
    ]

    subsidiary_top_df = subsidiary_top_df.reset_index(drop=True)
    subsidiary_top_df['top_subsidiary'] = subsidiary_top_df['subsidiary']
    subsidiary_top_df['top_subsidiary_tx_count'] = (
        subsidiary_top_df['subsidiary_tx_count']
    )
    subsidiary_top_df['top_subsidiary_amount'] = (
        subsidiary_top_df['subsidiary_amount']
    )

    subsidiary_top_df = subsidiary_top_df.loc[
        :,
        [
            *group_cols,
            'top_subsidiary',
            'top_subsidiary_tx_count',
            'top_subsidiary_amount',
        ],
    ]

    account_group_cols = _build_unique_cols([*group_cols, 'account_number'])

    account_df = data.groupby(
        account_group_cols,
        as_index=False,
    )

    account_df = account_df.agg(
        account_tx_count=('_id', 'size'),
        account_amount=('transaction_amount', 'sum'),
    )

    account_df['account_tx_share'] = (
        account_df['account_tx_count']
        / account_df.groupby(group_cols)['account_tx_count'].transform('sum')
    )

    account_df['account_amount_share'] = (
        account_df['account_amount']
        / account_df.groupby(group_cols)['account_amount'].transform('sum')
    )

    account_summary = account_df.groupby(
        group_cols,
        as_index=False,
    )

    account_summary = account_summary.agg(
        n_unique_accounts=('account_number', 'nunique'),
        top_account_tx_share=('account_tx_share', 'max'),
        top_account_amount_share=('account_amount_share', 'max'),
    )

    account_top_idx = account_df.groupby(group_cols)['account_tx_count'].idxmax()

    account_top_df = account_df.loc[
        account_top_idx,
        _build_unique_cols(
            [
            *group_cols,
            'account_number',
            'account_tx_count',
            'account_amount',
            ]
        ),
    ]

    account_top_df = account_top_df.reset_index(drop=True)
    account_top_df['top_account_number'] = account_top_df['account_number']
    account_top_df['top_account_tx_count'] = account_top_df['account_tx_count']
    account_top_df['top_account_amount'] = account_top_df['account_amount']

    account_top_df = account_top_df.loc[
        :,
        [
            *group_cols,
            'top_account_number',
            'top_account_tx_count',
            'top_account_amount',
        ],
    ]

    destination_df = merchant_summary.merge(
        merchant_top_df,
        on=group_cols,
        how='inner',
    )

    destination_df = destination_df.merge(
        subsidiary_summary,
        on=group_cols,
        how='inner',
    )

    destination_df = destination_df.merge(
        subsidiary_top_df,
        on=group_cols,
        how='inner',
    )

    destination_df = destination_df.merge(
        account_summary,
        on=group_cols,
        how='inner',
    )

    destination_df = destination_df.merge(
        account_top_df,
        on=group_cols,
        how='inner',
    )

    return destination_df


def merge_daily_baseline_features(
    alerts: pd.DataFrame,
    baseline_df: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Agrega z-scores de referencia a la tabla diaria de alertas.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        baseline_df: Tabla diaria con referencia del periodo observado.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame de alertas enriquecido con referencia del periodo.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    merge_cols = [*entity_cols, 'transaction_day']

    baseline_cols = [
        *merge_cols,
        'z_day_tx_count',
        'z_day_amount',
    ]

    alerts = alerts.merge(
        baseline_df.loc[:, baseline_cols],
        on=merge_cols,
        how='left',
    )

    return alerts


def merge_daily_destination_features(
    alerts: pd.DataFrame,
    destination_df: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Agrega features de cuenta y destino observable a la tabla diaria.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        destination_df: Tabla diaria con cuenta y destino observable.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame de alertas enriquecido con cuenta y destino.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    merge_cols = [*entity_cols, 'transaction_day']

    destination_cols = [
        *merge_cols,
        'top_account_number',
        'top_account_tx_count',
        'top_account_amount',
        'n_unique_accounts',
        'top_account_tx_share',
        'top_account_amount_share',
        'top_merchant_id',
        'top_merchant_tx_count',
        'top_merchant_amount',
        'top_merchant_n_subsidiaries',
        'top_merchant_tx_share',
        'top_merchant_amount_share',
        'n_unique_merchants',
        'max_subsidiaries_per_merchant',
        'top_subsidiary',
        'top_subsidiary_tx_count',
        'top_subsidiary_amount',
        'top_subsidiary_tx_share',
        'top_subsidiary_amount_share',
        'n_unique_subsidiaries',
    ]

    alerts = alerts.merge(
        destination_df.loc[:, destination_cols],
        on=merge_cols,
        how='left',
    )

    return alerts


def apply_destination_hypothesis_rules(
    alerts: pd.DataFrame,
    min_tx_count: int = 3,
) -> pd.DataFrame:
    """Aplica reglas de dispersion diaria por destino observable.

    Args:
        alerts: Tabla diaria de alertas con features de destino observable.
        min_tx_count: Minimo de transacciones para evaluar dispersion.

    Returns:
        DataFrame de alertas con reglas H4 resumidas por `transaction_day`.
    """
    alerts = alerts.reset_index(drop=True)

    alerts['multi_merchant_dispersion'] = (
        (alerts['n_unique_merchants'] > 1)
        & (alerts['count'] >= min_tx_count)
    ).fillna(False).astype(int)

    alerts['multi_subsidiary_dispersion'] = (
        (alerts['n_unique_subsidiaries'] > 1)
        & (alerts['count'] >= min_tx_count)
    ).fillna(False).astype(int)

    alerts['multi_subsidiary_same_merchant'] = (
        (alerts['top_merchant_tx_share'] >= 0.80)
        & (alerts['n_unique_subsidiaries'] > 1)
        & (alerts['count'] >= min_tx_count)
    ).fillna(False).astype(int)

    alerts['h4_destination_dispersion'] = (
        (alerts['multi_subsidiary_dispersion'] == 1)
        | (alerts['multi_merchant_dispersion'] == 1)
        | (alerts['multi_subsidiary_same_merchant'] == 1)
    ).fillna(False).astype(int)

    return alerts


def apply_hypothesis_rules(
    alerts: pd.DataFrame,
    tx_count_quantile: float = 0.95,
    amount_quantile: float = 0.95,
    cv_quantile: float = 0.25,
    z_tx_quantile: float = 0.95,
    z_amount_quantile: float = 0.95,
) -> pd.DataFrame:
    """Aplica reglas heuristicas a la tabla diaria de alertas.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        tx_count_quantile: Cuantil para alta frecuencia.
        amount_quantile: Cuantil para alto monto agregado.
        cv_quantile: Cuantil para baja variacion.
        z_tx_quantile: Cuantil para alta desviacion de frecuencia.
        z_amount_quantile: Cuantil para alta desviacion de monto.

    Returns:
        DataFrame de alertas con reglas activadas.
    """
    alerts = alerts.reset_index(drop=True)

    alerts = apply_window_hypothesis_rules(
        alerts=alerts,
        tx_count_quantile=tx_count_quantile,
        amount_quantile=amount_quantile,
        cv_quantile=cv_quantile,
    )

    alerts = apply_baseline_hypothesis_rules(
        alerts=alerts,
        z_tx_quantile=z_tx_quantile,
        z_amount_quantile=z_amount_quantile,
    )

    return alerts


def apply_window_hypothesis_rules(
    alerts: pd.DataFrame,
    tx_count_quantile: float = 0.95,
    amount_quantile: float = 0.95,
    cv_quantile: float = 0.25,
) -> pd.DataFrame:
    """Aplica reglas de frecuencia, monto y similitud en 24 horas.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        tx_count_quantile: Cuantil para alta frecuencia.
        amount_quantile: Cuantil para alto monto agregado.
        cv_quantile: Cuantil para baja variacion.

    Returns:
        DataFrame de alertas con reglas H1 y H2.
    """
    alerts = alerts.reset_index(drop=True)

    tx_count_threshold = alerts['count'].quantile(tx_count_quantile)
    amount_threshold = alerts['sum'].quantile(amount_quantile)
    cv_threshold = alerts['cv'].quantile(cv_quantile)

    alerts['h1_tx_count'] = (
        alerts['count'] >= tx_count_threshold
    ).astype(int)

    alerts['h1_amount'] = (
        alerts['sum'] >= amount_threshold
    ).astype(int)

    alerts['h2_low_cv'] = (
        (alerts['cv'] <= cv_threshold)
        & (alerts['count'] >= tx_count_threshold)
    )

    alerts['h2_low_cv'] = alerts['h2_low_cv'].fillna(False).astype(int)

    return alerts


def apply_baseline_hypothesis_rules(
    alerts: pd.DataFrame,
    z_tx_quantile: float = 0.95,
    z_amount_quantile: float = 0.95,
) -> pd.DataFrame:
    """Aplica reglas de desviacion frente a la referencia del periodo.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        z_tx_quantile: Cuantil para alta desviacion de frecuencia.
        z_amount_quantile: Cuantil para alta desviacion de monto.

    Returns:
        DataFrame de alertas con reglas H3.
    """
    alerts = alerts.reset_index(drop=True)

    z_tx_threshold = alerts['z_day_tx_count'].quantile(z_tx_quantile)
    z_amount_threshold = alerts['z_day_amount'].quantile(z_amount_quantile)

    alerts['h3_high_z_tx_count'] = (
        alerts['z_day_tx_count'] >= z_tx_threshold
    ).fillna(False).astype(int)

    alerts['h3_high_z_amount'] = (
        alerts['z_day_amount'] >= z_amount_threshold
    ).fillna(False).astype(int)

    return alerts


def build_heuristic_score_table(
    alerts: pd.DataFrame,
    entity_cols: list[str] | None = None,
    medium_quantile: float = 0.90,
    high_quantile: float = 0.95,
) -> pd.DataFrame:
    """Construye la tabla final de score heuristico.

    Args:
        alerts: Tabla diaria de alertas con reglas activadas.
        entity_cols: Columnas que definen la entidad de analisis.
        medium_quantile: Cuantil para alerta media.
        high_quantile: Cuantil para alerta alta.

    Returns:
        Tabla final de score y reglas activadas.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    score_df = alerts.rename(
        columns={
            'count': 'tx_count_24h',
            'sum': 'amount_24h',
            'mean': 'avg_amount_24h',
            'std': 'std_amount_24h',
            'cv': 'cv_amount_24h',
        }
    )

    rule_cols = [
        'h1_tx_count',
        'h1_amount',
        'h2_low_cv',
        'h3_high_z_tx_count',
        'h3_high_z_amount',
    ]

    score_df['heuristic_risk_score'] = score_df.loc[:, rule_cols].sum(axis=1)
    score_df['triggered_rules'] = ''

    score_df.loc[score_df['h1_tx_count'] == 1, 'triggered_rules'] = (
        score_df.loc[score_df['h1_tx_count'] == 1, 'triggered_rules']
        + 'H1_tx_count; '
    )

    score_df.loc[score_df['h1_amount'] == 1, 'triggered_rules'] = (
        score_df.loc[score_df['h1_amount'] == 1, 'triggered_rules']
        + 'H1_amount; '
    )

    score_df.loc[score_df['h2_low_cv'] == 1, 'triggered_rules'] = (
        score_df.loc[score_df['h2_low_cv'] == 1, 'triggered_rules']
        + 'H2_low_cv; '
    )

    score_df.loc[score_df['h3_high_z_tx_count'] == 1, 'triggered_rules'] = (
        score_df.loc[score_df['h3_high_z_tx_count'] == 1, 'triggered_rules']
        + 'H3_high_z_tx_count; '
    )

    score_df.loc[score_df['h3_high_z_amount'] == 1, 'triggered_rules'] = (
        score_df.loc[score_df['h3_high_z_amount'] == 1, 'triggered_rules']
        + 'H3_high_z_amount; '
    )

    score_df['triggered_rules'] = score_df['triggered_rules'].str.rstrip('; ')

    score_cols = [
        *entity_cols,
        'transaction_day',
        'tx_count_24h',
        'amount_24h',
        'avg_amount_24h',
        'std_amount_24h',
        'cv_amount_24h',
        'z_day_tx_count',
        'z_day_amount',
        'h1_tx_count',
        'h1_amount',
        'h2_low_cv',
        'h3_high_z_tx_count',
        'h3_high_z_amount',
        'heuristic_risk_score',
        'triggered_rules',
    ]

    score_df = score_df.loc[:, score_cols]

    score_df = score_df.sort_values(
        ['heuristic_risk_score', 'tx_count_24h', 'amount_24h'],
        ascending=[False, False, False],
    )

    score_df = score_df.reset_index(drop=True)

    medium_threshold = score_df['heuristic_risk_score'].quantile(medium_quantile)
    high_threshold = score_df['heuristic_risk_score'].quantile(high_quantile)

    score_df['alert_level'] = 'sin_alerta'

    score_df.loc[
        score_df['heuristic_risk_score'] >= medium_threshold,
        'alert_level',
    ] = 'media'

    score_df.loc[
        score_df['heuristic_risk_score'] >= high_threshold,
        'alert_level',
    ] = 'alta'

    score_df['is_alert'] = 0

    score_df.loc[
        score_df['heuristic_risk_score'] >= high_threshold,
        'is_alert',
    ] = 1

    return score_df


def build_segment_thresholds(
    alerts: pd.DataFrame,
    segment_cols: list[str] | None = None,
    tx_count_quantile: float = 0.95,
    amount_quantile: float = 0.95,
    cv_quantile: float = 0.25,
) -> pd.DataFrame:
    """Construye umbrales por segmento para el motor de escenarios.

    Args:
        alerts: Tabla diaria de alertas candidatas.
        segment_cols: Columnas usadas para segmentar los umbrales.
        tx_count_quantile: Cuantil para alta frecuencia.
        amount_quantile: Cuantil para alto monto agregado.
        cv_quantile: Cuantil para baja variacion.

    Returns:
        DataFrame con umbrales por segmento.
    """
    if segment_cols is None:
        segment_cols = ['transaction_type']

    threshold_df = alerts.groupby(
        segment_cols,
        as_index=False,
    )

    threshold_df = threshold_df.agg(
        tx_count_threshold=('count', lambda values: values.quantile(tx_count_quantile)),
        amount_threshold=('sum', lambda values: values.quantile(amount_quantile)),
        cv_low_threshold=('cv', lambda values: values.quantile(cv_quantile)),
    )

    return threshold_df


def build_scenario_alert_table(
    alerts: pd.DataFrame,
    entity_cols: list[str] | None = None,
    segment_cols: list[str] | None = None,
    min_tx_count: int = 3,
    z_score_threshold: float = 2.0,
) -> pd.DataFrame:
    """Construye una tabla final de alertas basada en escenarios.

    Args:
        alerts: Tabla diaria de alertas con referencia del periodo.
        entity_cols: Columnas que definen la entidad de analisis.
        segment_cols: Columnas usadas para segmentar los umbrales.
        min_tx_count: Minimo de transacciones para considerar fraccionamiento.
        z_score_threshold: Umbral de anomalia contra la referencia del periodo.

    Returns:
        Tabla final de alertas y conteo de escenarios activados.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    if segment_cols is None:
        segment_cols = ['transaction_type']

    threshold_df = build_segment_thresholds(
        alerts=alerts,
        segment_cols=segment_cols,
    )

    alert_table = alerts.merge(
        threshold_df,
        on=segment_cols,
        how='left',
    )

    alert_table['high_tx_count_24h'] = (
        (alert_table['count'] >= alert_table['tx_count_threshold'])
        & (alert_table['count'] >= min_tx_count)
    ).astype(int)

    alert_table['high_amount_24h'] = (
        (alert_table['sum'] >= alert_table['amount_threshold'])
        & (alert_table['count'] >= min_tx_count)
    ).astype(int)

    alert_table['low_cv_24h'] = (
        (alert_table['cv'] <= alert_table['cv_low_threshold'])
        & (alert_table['count'] >= min_tx_count)
    )

    alert_table['low_cv_24h'] = alert_table['low_cv_24h'].fillna(False).astype(int)

    alert_table['anomalous_tx_count'] = (
        alert_table['z_day_tx_count'] >= z_score_threshold
    ).fillna(False).astype(int)

    alert_table['anomalous_amount'] = (
        alert_table['z_day_amount'] >= z_score_threshold
    ).fillna(False).astype(int)

    alert_table = apply_destination_hypothesis_rules(
        alerts=alert_table,
        min_tx_count=min_tx_count,
    )

    alert_table['scenario_burst_similar'] = (
        (alert_table['high_tx_count_24h'] == 1)
        & (alert_table['low_cv_24h'] == 1)
    ).astype(int)

    alert_table['scenario_burst_anomalous'] = (
        (alert_table['high_tx_count_24h'] == 1)
        & (
            (alert_table['anomalous_tx_count'] == 1)
            | (alert_table['anomalous_amount'] == 1)
        )
    ).astype(int)

    alert_table['scenario_material_amount'] = (
        (alert_table['high_amount_24h'] == 1)
        & (
            (alert_table['low_cv_24h'] == 1)
            | (alert_table['anomalous_amount'] == 1)
            | (alert_table['anomalous_tx_count'] == 1)
        )
    ).astype(int)

    alert_table['scenario_destination_dispersion'] = (
        (alert_table['high_tx_count_24h'] == 1)
        & (alert_table['h4_destination_dispersion'] == 1)
    ).astype(int)

    scenario_cols = [
        'scenario_burst_similar',
        'scenario_burst_anomalous',
        'scenario_material_amount',
        'scenario_destination_dispersion',
    ]

    alert_table['scenario_count'] = alert_table.loc[:, scenario_cols].sum(axis=1)

    alert_table['alert_level'] = 'sin_alerta'

    alert_table.loc[
        alert_table['scenario_count'] == 1,
        'alert_level',
    ] = 'pre_alerta'

    alert_table.loc[
        alert_table['scenario_count'] >= 2,
        'alert_level',
    ] = 'media'

    alert_table.loc[
        alert_table['scenario_count'] >= 3,
        'alert_level',
    ] = 'alta'

    alert_table['is_alert'] = 0

    alert_table.loc[
        alert_table['alert_level'].isin(['media', 'alta']),
        'is_alert',
    ] = 1

    alert_table['window_end'] = alert_table['transaction_date']
    alert_table['window_start'] = (
        alert_table['window_end'] - pd.Timedelta(hours=24)
    )

    alert_table = alert_table.rename(
        columns={
            'count': 'tx_count_24h',
            'sum': 'amount_24h',
            'mean': 'avg_amount_24h',
            'std': 'std_amount_24h',
            'cv': 'cv_amount_24h',
        }
    )

    final_cols = [
        *entity_cols,
        'transaction_day',
        'window_start',
        'window_end',
        'tx_count_24h',
        'amount_24h',
        'avg_amount_24h',
        'std_amount_24h',
        'cv_amount_24h',
        'top_account_number',
        'top_account_tx_count',
        'top_account_amount',
        'n_unique_accounts',
        'top_account_tx_share',
        'top_account_amount_share',
        'top_merchant_id',
        'top_merchant_tx_count',
        'top_merchant_amount',
        'top_merchant_n_subsidiaries',
        'top_merchant_tx_share',
        'top_merchant_amount_share',
        'n_unique_merchants',
        'max_subsidiaries_per_merchant',
        'top_subsidiary',
        'top_subsidiary_tx_count',
        'top_subsidiary_amount',
        'top_subsidiary_tx_share',
        'top_subsidiary_amount_share',
        'n_unique_subsidiaries',
        'tx_count_threshold',
        'amount_threshold',
        'cv_low_threshold',
        'z_day_tx_count',
        'z_day_amount',
        'high_tx_count_24h',
        'high_amount_24h',
        'low_cv_24h',
        'anomalous_tx_count',
        'anomalous_amount',
        'multi_merchant_dispersion',
        'multi_subsidiary_dispersion',
        'multi_subsidiary_same_merchant',
        'scenario_burst_similar',
        'scenario_burst_anomalous',
        'scenario_material_amount',
        'scenario_destination_dispersion',
        'scenario_count',
        'alert_level',
        'is_alert',
    ]

    final_cols = _build_unique_cols(final_cols)
    alert_table = alert_table.loc[:, final_cols]

    alert_table = alert_table.sort_values(
        ['is_alert', 'scenario_count', 'tx_count_24h', 'amount_24h'],
        ascending=[False, False, False, False],
    )

    alert_table = alert_table.reset_index(drop=True)

    return alert_table


def select_alert_example(
    alert_table: pd.DataFrame,
    alert_level: str = 'alta',
) -> pd.DataFrame:
    """Selecciona un ejemplo representativo de alerta.

    Args:
        alert_table: Tabla final de alertas basada en escenarios.
        alert_level: Nivel de alerta a priorizar.

    Returns:
        DataFrame con un solo ejemplo de alerta.
    """
    example_df = alert_table.loc[
        alert_table['alert_level'] == alert_level,
    ]

    example_df = example_df.sort_values(
        ['scenario_count', 'tx_count_24h', 'amount_24h'],
        ascending=[False, False, False],
    )

    example_df = example_df.head(1)
    example_df = example_df.reset_index(drop=True)

    return example_df


def build_alert_example_transactions(
    data: pd.DataFrame,
    example_df: pd.DataFrame,
    entity_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Recupera las transacciones de un ejemplo dentro de su ventana.

    Args:
        data: DataFrame de transacciones limpio.
        example_df: DataFrame con un solo ejemplo de alerta.
        entity_cols: Columnas que definen la entidad de analisis.

    Returns:
        DataFrame con las transacciones del ejemplo y monto acumulado.
    """
    entity_cols = _resolve_entity_cols(entity_cols)

    example_row = example_df.iloc[0]

    mask = data.loc[:, 'transaction_date'].between(
        example_row['window_start'],
        example_row['window_end'],
    )

    entity_mask = data.loc[:, entity_cols].eq(
        example_row.loc[entity_cols]
    ).all(axis=1)

    mask = mask & entity_mask

    example_tx_df = data.loc[
        mask,
        _build_unique_cols(
            [
            *entity_cols,
            '_id',
            'transaction_date',
            'account_number',
            'merchant_id',
            'subsidiary',
            'transaction_amount',
            ]
        ),
    ]

    example_tx_df = example_tx_df.sort_values('transaction_date')
    example_tx_df = example_tx_df.reset_index(drop=True)
    example_tx_df['cumulative_amount'] = (
        example_tx_df['transaction_amount'].cumsum()
    )

    return example_tx_df


def plot_alert_example(
    example_tx_df: pd.DataFrame,
    example_df: pd.DataFrame,
) -> None:
    """Grafica un ejemplo puntual de alerta en su ventana de 24 horas.

    Args:
        example_tx_df: Transacciones del ejemplo dentro de la ventana.
        example_df: DataFrame con un solo ejemplo de alerta.
    """
    example_row = example_df.iloc[0]

    fig, ax1 = plt.subplots(figsize=(16, 5))

    sns.lineplot(
        data=example_tx_df,
        x='transaction_date',
        y='transaction_amount',
        marker='o',
        ax=ax1,
        label='monto individual',
    )

    ax1.set_xlabel('Fecha y hora')
    ax1.set_ylabel('Monto individual')
    ax1.tick_params(axis='x', rotation=45)

    ax2 = ax1.twinx()

    sns.lineplot(
        data=example_tx_df,
        x='transaction_date',
        y='cumulative_amount',
        marker='o',
        color='black',
        ax=ax2,
        label='monto acumulado',
    )

    ax2.set_ylabel('Monto acumulado')

    title = (
        'Ejemplo de alerta '
        f"{example_row['alert_level']} | "
        f"{example_row['transaction_type']} | "
        f"escenarios={example_row['scenario_count']}"
    )

    ax1.set_title(title)
    fig.tight_layout()
    plt.show()


def build_alert_level_monitoring_table(
    alert_table: pd.DataFrame,
    day_col: str = 'transaction_day',
) -> pd.DataFrame:
    """Resume volumen y tasa diaria por nivel de alerta.

    Args:
        alert_table: Tabla final de alertas basada en escenarios.
        day_col: Columna diaria usada para el monitoreo.

    Returns:
        DataFrame con volumen total y metricas diarias por `alert_level`.
    """
    day_values = alert_table.loc[:, day_col].drop_duplicates().sort_values()

    level_order = [
        'sin_alerta',
        'pre_alerta',
        'media',
        'alta',
    ]

    level_values = pd.DataFrame({'alert_level': level_order})
    day_df = pd.DataFrame({day_col: day_values})

    monitoring_df = day_df.merge(level_values, how='cross')

    counts_df = alert_table.groupby(
        [day_col, 'alert_level'],
        as_index=False,
    )

    counts_df = counts_df.agg(
        n_cases=('alert_level', 'size'),
    )

    monitoring_df = monitoring_df.merge(
        counts_df,
        on=[day_col, 'alert_level'],
        how='left',
    )

    monitoring_df['n_cases'] = monitoring_df['n_cases'].fillna(0)

    total_df = alert_table.groupby(
        day_col,
        as_index=False,
    )

    total_df = total_df.agg(
        day_total=('alert_level', 'size'),
    )

    monitoring_df = monitoring_df.merge(
        total_df,
        on=day_col,
        how='left',
    )

    monitoring_df['daily_rate'] = (
        monitoring_df['n_cases'] / monitoring_df['day_total']
    )

    summary_df = monitoring_df.groupby(
        'alert_level',
        as_index=False,
    )

    summary_df = summary_df.agg(
        volume=('n_cases', 'sum'),
        avg_daily_volume=('n_cases', 'mean'),
        avg_daily_rate=('daily_rate', 'mean'),
        p95_daily_volume=('n_cases', lambda values: values.quantile(0.95)),
    )

    summary_df['pct_total'] = (
        100 * summary_df['volume'] / len(alert_table)
    )

    summary_df['alert_level'] = pd.Categorical(
        summary_df['alert_level'],
        categories=level_order,
        ordered=True,
    )

    summary_df = summary_df.sort_values('alert_level')
    summary_df = summary_df.reset_index(drop=True)

    return summary_df


def build_daily_alert_series(
    alert_table: pd.DataFrame,
    alert_level: str = 'alta',
    day_col: str = 'transaction_day',
) -> pd.DataFrame:
    """Construye serie diaria para un nivel de alerta.

    Args:
        alert_table: Tabla final de alertas basada en escenarios.
        alert_level: Nivel de alerta a monitorear.
        day_col: Columna diaria usada para el monitoreo.

    Returns:
        DataFrame con volumen diario y promedio movil.
    """
    day_values = alert_table.loc[:, day_col].drop_duplicates().sort_values()
    series_df = pd.DataFrame({day_col: day_values})

    level_df = alert_table.loc[
        alert_table['alert_level'] == alert_level,
        [day_col, 'alert_level'],
    ]

    level_df = level_df.groupby(
        day_col,
        as_index=False,
    )

    level_df = level_df.agg(
        n_cases=('alert_level', 'size'),
    )

    series_df = series_df.merge(
        level_df,
        on=day_col,
        how='left',
    )

    series_df['n_cases'] = series_df['n_cases'].fillna(0)
    series_df['rolling_mean_7d'] = (
        series_df['n_cases'].rolling(7, min_periods=1).mean()
    )

    return series_df


def plot_daily_alert_series(
    series_df: pd.DataFrame,
    alert_level: str = 'alta',
    day_col: str = 'transaction_day',
) -> None:
    """Grafica la serie diaria de un nivel de alerta.

    Args:
        series_df: Serie diaria construida para un nivel de alerta.
        alert_level: Nivel de alerta graficado.
        day_col: Columna diaria usada como eje x.
    """
    plt.figure(figsize=(16, 5))

    sns.lineplot(
        data=series_df,
        x=day_col,
        y='n_cases',
        label=f'volumen diario {alert_level}',
    )

    sns.lineplot(
        data=series_df,
        x=day_col,
        y='rolling_mean_7d',
        label='promedio movil 7 dias',
    )

    plt.title(f'Serie diaria de alertas {alert_level}')
    plt.xlabel('Fecha')
    plt.ylabel('Numero de casos')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def build_top_scenario_counts(
    alert_table: pd.DataFrame,
    top_n: int = 10,
) -> pd.DataFrame:
    """Resume los conteos de escenarios mas frecuentes.

    Args:
        alert_table: Tabla final de alertas basada en escenarios.
        top_n: Numero de filas a retornar.

    Returns:
        DataFrame con los conteos de escenarios mas frecuentes.
    """
    combo_df = alert_table.loc[
        alert_table['scenario_count'] > 0,
        ['scenario_count', 'alert_level'],
    ]

    combo_df = combo_df.groupby(
        ['scenario_count', 'alert_level'],
        as_index=False,
    )

    combo_df = combo_df.agg(
        n_cases=('alert_level', 'size'),
    )

    combo_df['pct_cases'] = (
        100 * combo_df['n_cases'] / combo_df['n_cases'].sum()
    )

    combo_df = combo_df.sort_values(
        ['n_cases', 'scenario_count', 'alert_level'],
        ascending=[False, False, True],
    )

    combo_df = combo_df.head(top_n)
    combo_df = combo_df.reset_index(drop=True)

    return combo_df


def build_scenario_detection_table(
    data: pd.DataFrame,
    entity_cols: list[str] | None = None,
    segment_cols: list[str] | None = None,
    window: str = '24h',
) -> pd.DataFrame:
    """Ejecuta el flujo completo de deteccion basado en escenarios.

    Args:
        data: DataFrame de transacciones limpio.
        entity_cols: Columnas que definen la entidad de analisis.
        segment_cols: Columnas usadas para segmentar los umbrales.
        window: Tamano de la ventana movil.

    Returns:
        Tabla final de alertas basada en escenarios.
    """
    window_features = build_window_features(
        data=data,
        entity_cols=entity_cols,
        window=window,
    )

    alerts = build_daily_window_alerts(
        window_features=window_features,
        entity_cols=entity_cols,
    )

    baseline_df = build_daily_baseline_features(
        data=data,
        entity_cols=entity_cols,
    )

    destination_df = build_daily_destination_features(
        data=data,
        entity_cols=entity_cols,
    )

    alerts = merge_daily_baseline_features(
        alerts=alerts,
        baseline_df=baseline_df,
        entity_cols=entity_cols,
    )

    alerts = merge_daily_destination_features(
        alerts=alerts,
        destination_df=destination_df,
        entity_cols=entity_cols,
    )

    alert_table = build_scenario_alert_table(
        alerts=alerts,
        entity_cols=entity_cols,
        segment_cols=segment_cols,
    )

    return alert_table


def build_detection_table(
    data: pd.DataFrame,
    entity_cols: list[str] | None = None,
    window: str = '24h',
) -> pd.DataFrame:
    """Ejecuta el flujo completo de deteccion heuristica.

    Args:
        data: DataFrame de transacciones limpio.
        entity_cols: Columnas que definen la entidad de analisis.
        window: Tamano de la ventana movil.

    Returns:
        Tabla final de alertas con score heuristico.
    """
    window_features = build_window_features(
        data=data,
        entity_cols=entity_cols,
        window=window,
    )

    alerts = build_daily_window_alerts(
        window_features=window_features,
        entity_cols=entity_cols,
    )

    baseline_df = build_daily_baseline_features(
        data=data,
        entity_cols=entity_cols,
    )

    destination_df = build_daily_destination_features(
        data=data,
        entity_cols=entity_cols,
    )

    alerts = merge_daily_baseline_features(
        alerts=alerts,
        baseline_df=baseline_df,
        entity_cols=entity_cols,
    )

    alerts = merge_daily_destination_features(
        alerts=alerts,
        destination_df=destination_df,
        entity_cols=entity_cols,
    )

    alerts = apply_hypothesis_rules(alerts=alerts)
    score_df = build_heuristic_score_table(
        alerts=alerts,
        entity_cols=entity_cols,
    )

    return score_df
