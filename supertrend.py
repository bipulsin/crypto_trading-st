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

def calculate_supertrend_enhanced(df, period=10, multiplier=3, logger=None):
    """Enhanced SuperTrend calculation with better error handling and logging"""
    if len(df) < period:
        if logger:
            logger.warning(f"Insufficient data for SuperTrend calculation. Need {period}, got {len(df)}")
        return df
    
    if ta is None:
        if logger:
            logger.error("pandas_ta is required for SuperTrend calculation")
        return df
    
    try:
        # Calculate SuperTrend
        supertrend = ta.supertrend(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            length=period,
            multiplier=multiplier
        )
        
        # Debug: Log the actual column names returned by pandas_ta
        if logger:
            logger.info(f"SuperTrend columns: {list(supertrend.columns)}")
        
        # The pandas_ta supertrend function returns columns with different naming
        # Let's find the correct column names
        supertrend_cols = [col for col in supertrend.columns if 'SUPERT' in col]
        direction_cols = [col for col in supertrend.columns if 'SUPERTd' in col]
        
        if not supertrend_cols or not direction_cols:
            if logger:
                logger.error(f"SuperTrend columns not found. Available columns: {list(supertrend.columns)}")
            return df
        
        # Use the first found columns
        supertrend_col = supertrend_cols[0]
        direction_col = direction_cols[0]
        
        if logger:
            logger.info(f"Using SuperTrend columns: {supertrend_col}, {direction_col}")
        
        # Add the SuperTrend data to the dataframe
        df['supertrend_value'] = supertrend[supertrend_col]
        df['trend_direction'] = supertrend[direction_col]
        
        return df
        
    except Exception as e:
        if logger:
            logger.error(f"Error calculating SuperTrend: {e}")
        return df
