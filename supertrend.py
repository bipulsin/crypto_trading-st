import warnings
import pandas as pd
try:
    import pandas_ta as ta
except ImportError:
    ta = None

# Suppress pkg_resources deprecation warning from pandas_ta
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

def calculate_supertrend(df, period=10, multiplier=3):
    if ta is not None:
        st = ta.supertrend(df['high'], df['low'], df['close'], length=period, multiplier=multiplier)
        df = df.copy()
        if st is not None:
            for col in st.columns:
                df[col] = st[col]
            supertrend_col = None
            supertrend_signal_col = None
            for col in st.columns:
                if col.startswith('SUPERT_') and not col.startswith('SUPERTd_') and not col.startswith('SUPERTl_') and not col.startswith('SUPERTs_'):
                    supertrend_col = col
                elif col.startswith('SUPERTd_'):
                    supertrend_signal_col = col
            if supertrend_col is not None:
                df['supertrend'] = df[supertrend_col]
            else:
                for col in st.columns:
                    if col.startswith('SUPERT'):
                        df['supertrend'] = df[col]
                        break
                else:
                    df['supertrend'] = df[st.columns[0]]
            if supertrend_signal_col is not None:
                df['supertrend_signal'] = df[supertrend_signal_col].apply(lambda x: 1 if x == 1 else -1)
            else:
                for col in st.columns:
                    if col.startswith('SUPERTd_'):
                        df['supertrend_signal'] = df[col].apply(lambda x: 1 if x == 1 else -1)
                        break
                else:
                    df['supertrend_signal'] = 0
        else:
            df['supertrend_signal'] = 0
        return df
    else:
        raise ImportError('pandas_ta is required for SuperTrend calculation')
