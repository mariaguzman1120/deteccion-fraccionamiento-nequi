'''Utilidades de lectura de datos.'''

from pathlib import Path

import pandas as pd


def load_data(path: str | Path) -> pd.DataFrame:
    '''Lee el archivo de transacciones y aplica limpieza base de tipos.

    Args:
        path: Ruta del archivo fuente.

    Returns:
        DataFrame con la data cargada y tipada.
    '''
    df = pd.read_parquet(path)

    if 'transaction_date' in df.columns:
        df['transaction_date'] = pd.to_datetime(
            df['transaction_date'], errors='coerce'
        )

        df['transaction_day'] = df['transaction_date'].dt.date
        df['transaction_time'] = df['transaction_date'].dt.time

    if 'transaction_amount' in df.columns:
        df['transaction_amount'] = df['transaction_amount'].astype(float)

    return df
