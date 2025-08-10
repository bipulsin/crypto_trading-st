# SuperTrend Strategy Configuration Implementation

## Overview
This document describes the implementation of the crypto coin selection dropdown and automatic symbol ID mapping for the SuperTrend strategy configuration page.

## Features Implemented

### 1. Crypto Coin Dropdown
- **Location**: Trading Configuration section of the config dashboard
- **Options**: 
  - BTCUSD (Bitcoin/USD)
  - ETHUSD (Ethereum/USD)
- **Required Field**: Yes
- **Default Value**: BTCUSD

### 2. Broker Connection Selection
- **Location**: Trading Configuration section of the config dashboard
- **Purpose**: Determines whether the connection is testnet or live
- **Required Field**: Yes
- **Dynamic Loading**: Populated from user's broker connections

### 3. Automatic Symbol ID Mapping
The system automatically determines the correct symbol ID based on:
- Selected crypto coin (BTCUSD or ETHUSD)
- Broker connection type (testnet vs live)

#### Symbol ID Mapping Table

| Coin | Environment | Symbol ID |
|------|-------------|-----------|
| BTCUSD | Testnet | 84 |
| BTCUSD | Live | 27 |
| ETHUSD | Testnet | 3137* |
| ETHUSD | Live | 3136 |

*Note: ETHUSD testnet symbol ID (3137) is a placeholder value. The actual testnet symbol ID for ETHUSD on Delta Exchange should be verified and updated.

## Technical Implementation

### Database Schema Changes
The `strategy_configs` table has been updated with new columns:

```sql
ALTER TABLE strategy_configs ADD COLUMN symbol TEXT NOT NULL DEFAULT 'BTCUSD';
ALTER TABLE strategy_configs ADD COLUMN symbol_id INTEGER NOT NULL DEFAULT 84;
```

### New API Endpoints

#### GET /api/config
Retrieves the current SuperTrend strategy configuration including:
- Broker connection ID
- Selected symbol (BTCUSD/ETHUSD)
- Calculated symbol ID
- Configuration data (leverage, position size, etc.)
- Active status

#### POST /api/config
Saves the SuperTrend strategy configuration:
1. Validates input data
2. Determines symbol ID based on symbol and broker connection
3. Stores configuration in database
4. Returns success/error response

### Symbol ID Logic
The `get_symbol_id()` function:
1. Retrieves broker connection URL from database
2. Determines if connection is testnet or live
3. Maps symbol to appropriate symbol ID
4. Returns default values if connection not found

```python
def get_symbol_id(symbol, broker_connection_id):
    # Get broker URL from database
    # Check if testnet (contains 'testnet' or 'sandbox' in URL)
    # Return appropriate symbol ID based on symbol and environment
```

## Frontend Changes

### HTML Template Updates
- Added crypto coin dropdown with BTCUSD/ETHUSD options
- Added broker connection selection dropdown
- Both fields are required for form submission

### JavaScript Enhancements
- `loadBrokerConnections()`: Dynamically loads user's broker connections
- `populateForm()`: Handles form population including new fields
- Form submission includes symbol and broker_connection_id

## Usage Workflow

1. **User Access**: Navigate to SuperTrend strategy configuration page
2. **Coin Selection**: Choose between BTCUSD or ETHUSD from dropdown
3. **Broker Selection**: Select appropriate broker connection (testnet/live)
4. **Configuration**: Set other trading parameters (leverage, position size, etc.)
5. **Save**: Configuration is saved with automatic symbol ID calculation
6. **Database Storage**: Symbol and symbol ID are stored for strategy execution

## Benefits

1. **User-Friendly**: Simple dropdown selection instead of manual symbol ID entry
2. **Error Prevention**: Automatic symbol ID calculation prevents configuration errors
3. **Environment Aware**: Automatically handles testnet vs live environments
4. **Extensible**: Easy to add more crypto coins in the future
5. **Data Integrity**: Ensures symbol and symbol ID are always in sync

## Future Enhancements

1. **Additional Coins**: Add more cryptocurrency pairs (SOLUSD, DOGEUSD, etc.)
2. **Real-time Validation**: Verify symbol IDs against exchange API
3. **Symbol Search**: Add search functionality for large coin lists
4. **Custom Symbols**: Allow users to add custom symbol mappings
5. **Symbol Info**: Display additional information about selected symbols

## Testing

The implementation has been tested with:
- Database schema migration
- Symbol ID mapping logic
- Configuration storage and retrieval
- Frontend form handling
- API endpoint functionality

## Notes

- The ETHUSD testnet symbol ID (3137) is currently a placeholder
- Users should verify the actual testnet symbol IDs with Delta Exchange
- The system gracefully handles missing broker connections with default values
- All existing configurations will work with the new schema (backward compatible)
