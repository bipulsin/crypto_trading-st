import warnings
import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    ta = None

# Suppress pkg_resources deprecation warning from pandas_ta
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

def calculate_supertrend(df, period=10, multiplier=3):
    """Legacy SuperTrend calculation function for backward compatibility"""
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
        # Validate input data
        required_columns = ['high', 'low', 'close']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            if logger:
                logger.error(f"Missing required columns: {missing_columns}")
            return df
        
        # Check for NaN values in required columns
        if df[required_columns].isnull().any().any():
            if logger:
                logger.warning("NaN values found in OHLC data, cleaning...")
            df = df.dropna(subset=required_columns)
            if len(df) < period:
                if logger:
                    logger.error(f"After cleaning NaN values, insufficient data: {len(df)} < {period}")
                return df
        
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
        supertrend_cols = [col for col in supertrend.columns if 'SUPERT' in col and not col.startswith('SUPERTd') and not col.startswith('SUPERTl') and not col.startswith('SUPERTs')]
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
        
        # Clean up any NaN values that might have been introduced
        df = df.dropna(subset=['supertrend_value', 'trend_direction'])
        
        # Ensure trend_direction is properly formatted (1 for bullish, -1 for bearish)
        df['trend_direction'] = df['trend_direction'].apply(lambda x: 1 if x == 1 else -1)
        
        if logger:
            logger.info(f"SuperTrend calculation completed successfully. Data points: {len(df)}")
        
        return df
        
    except Exception as e:
        if logger:
            logger.error(f"Error calculating SuperTrend: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        return df

def calculate_supertrend_manual(df, period=10, multiplier=3, logger=None):
    """Manual SuperTrend calculation as fallback when pandas_ta fails"""
    if logger:
        logger.info("Using manual SuperTrend calculation as fallback")
    
    try:
        df = df.copy()
        
        # Calculate ATR (Average True Range)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=period).mean()
        
        # Calculate SuperTrend
        df['upperband'] = ((df['high'] + df['low']) / 2) + (multiplier * df['atr'])
        df['lowerband'] = ((df['high'] + df['low']) / 2) - (multiplier * df['atr'])
        
        # Initialize SuperTrend
        df['supertrend_value'] = 0.0
        df['trend_direction'] = 0
        
        for i in range(period, len(df)):
            if df['close'].iloc[i] > df['upperband'].iloc[i-1]:
                df.loc[df.index[i], 'trend_direction'] = 1
            elif df['close'].iloc[i] < df['lowerband'].iloc[i-1]:
                df.loc[df.index[i], 'trend_direction'] = -1
            else:
                df.loc[df.index[i], 'trend_direction'] = df['trend_direction'].iloc[i-1]
            
            # Calculate SuperTrend value
            if df['trend_direction'].iloc[i] == 1:
                df.loc[df.index[i], 'supertrend_value'] = df['lowerband'].iloc[i]
            else:
                df.loc[df.index[i], 'supertrend_value'] = df['upperband'].iloc[i]
        
        # Clean up temporary columns
        df = df.drop(['tr1', 'tr2', 'tr3', 'tr', 'atr', 'upperband', 'lowerband'], axis=1)
        
        if logger:
            logger.info("Manual SuperTrend calculation completed successfully")
        
        return df
        
    except Exception as e:
        if logger:
            logger.error(f"Error in manual SuperTrend calculation: {e}")
        return df
