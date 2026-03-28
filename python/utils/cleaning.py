'''Utilidades de limpieza de datos.'''

import pandas as pd


def deduplicate_transaction_ids(
    data: pd.DataFrame,
    max_duplicate_time_gap_s: int = 5,
) -> pd.DataFrame:
    '''Elimina duplicados seguros de `_id`.

    Args:
        data: DataFrame con las transacciones.
        max_duplicate_time_gap_s: Diferencia maxima permitida entre duplicados.

    Returns:
        DataFrame sin duplicados seguros de `_id`.
    '''
    business_cols = [
        'user_id',
        'account_number',
        'merchant_id',
        'subsidiary',
        'transaction_amount',
        'transaction_type',
    ]

    dup_mask = data.loc[:, '_id'].duplicated(keep=False)

    if not dup_mask.any():
        return data

    duplicate_data = data.loc[
        dup_mask,
        ['_id', 'transaction_date', *business_cols],
    ]

    dup_summary = duplicate_data.groupby('_id', sort=False)

    dup_summary = dup_summary.agg(
        min_transaction_date=('transaction_date', 'min'),
        max_transaction_date=('transaction_date', 'max'),
        user_id_nunique=('user_id', 'nunique'),
        account_number_nunique=('account_number', 'nunique'),
        merchant_id_nunique=('merchant_id', 'nunique'),
        subsidiary_nunique=('subsidiary', 'nunique'),
        transaction_amount_nunique=('transaction_amount', 'nunique'),
        transaction_type_nunique=('transaction_type', 'nunique'),
    )

    business_nunique_cols = [
        'user_id_nunique',
        'account_number_nunique',
        'merchant_id_nunique',
        'subsidiary_nunique',
        'transaction_amount_nunique',
        'transaction_type_nunique',
    ]

    consistent_mask = dup_summary.loc[:, business_nunique_cols].eq(1).all(axis=1)

    time_gap_s = (
        dup_summary.loc[:, 'max_transaction_date']
        - dup_summary.loc[:, 'min_transaction_date']
    )

    time_gap_s = time_gap_s.dt.total_seconds()

    close_in_time_mask = time_gap_s <= max_duplicate_time_gap_s

    safe_ids = dup_summary.index[consistent_mask & close_in_time_mask]

    if len(safe_ids) == 0:
        return data

    safe_dup_mask = dup_mask & data.loc[:, '_id'].isin(safe_ids)

    duplicate_order = data.loc[safe_dup_mask, '_id'].groupby(data.loc[safe_dup_mask, '_id'])
    duplicate_order = duplicate_order.cumcount()

    drop_index = duplicate_order.loc[duplicate_order > 0].index

    cleaned_data = data.drop(index=drop_index)
    cleaned_data = cleaned_data.reset_index(drop=True)

    return cleaned_data


def drop_null_required_fields(data: pd.DataFrame) -> pd.DataFrame:
    '''Elimina filas con nulos en campos obligatorios.

    Args:
        data: DataFrame con las transacciones.

    Returns:
        DataFrame sin nulos en campos obligatorios.
    '''
    required_fields = [
        '_id',
        'transaction_date',
        'account_number',
        'user_id',
        'transaction_amount',
        'transaction_type',
    ]

    valid_mask = data.loc[:, required_fields].notna().all(axis=1)

    cleaned_data = data.loc[valid_mask]
    cleaned_data = cleaned_data.reset_index(drop=True)

    return cleaned_data


def drop_non_positive_transaction_amounts(data: pd.DataFrame) -> pd.DataFrame:
    '''Elimina filas con montos no positivos.

    Args:
        data: DataFrame con las transacciones.

    Returns:
        DataFrame sin montos menores o iguales a cero.
    '''
    valid_mask = data.loc[:, 'transaction_amount'] > 0

    cleaned_data = data.loc[valid_mask]
    cleaned_data = cleaned_data.reset_index(drop=True)

    return cleaned_data
