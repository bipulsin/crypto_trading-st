# Trade Manthan Web Application

A beautiful, modern web interface for the Trade Manthan automated trading platform with Google OAuth authentication.

## Features

- **Google OAuth Authentication**: Secure login with Google accounts
- **User Management**: Unique user IDs (TM99999 format) with personalized settings
- **Responsive Design**: Mobile-friendly interface with hamburger menu
- **Dashboard**: Real-time broker connections and market data
- **Strategy Management**: SuperTrend strategy with live controls
- **Broker Setup**: Add and manage multiple broker connections
- **Settings**: User-specific trading parameters

## Layout Structure

### Title Section (15-20% of page)
- Logo and "Trade Manthan" header
- "The automated trade platform" subtitle
- Welcome message with user name/email
- Current date and time

### Main Content (80-85% of page)
- **Left Sidebar (30% on desktop, hamburger on mobile)**:
  - Dashboard (default)
  - Strategy (Supertrend, RSI-EMA, Bollinger Band)
  - Broker Setup
  - Settings
  - Reports
  - Logout

- **Right Content Panel (70% on desktop, full on mobile)**:
  - Dynamic content based on menu selection

## Setup Instructions

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Set authorized redirect URIs:
   - `http://localhost:5000/callback` (for development)
   - `https://yourdomain.com/callback` (for production)

### 3. Environment Variables

Set the following environment variables:

```bash
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export GOOGLE_REDIRECT_URI="http://localhost:5000/callback"
export FLASK_SECRET_KEY="your-secret-key"
```

### 4. Run the Application

```bash
python3 start_app.py
```

Or directly:

```bash
python3 app.py
```

### 5. Access the Application

Open your browser and go to: `http://localhost:5000`

## Database Schema

The application uses SQLite with the following tables:

### Users Table
- `id`: Auto-increment primary key
- `user_id`: Unique TM99999 format ID
- `google_id`: Google OAuth ID
- `name`: User's full name
- `email`: User's email address
- `profile_picture`: Google profile picture URL
- `created_at`: Account creation timestamp
- `last_login`: Last login timestamp

### Broker Connections Table
- `id`: Auto-increment primary key
- `user_id`: Foreign key to users table
- `connection_name`: Display name for the connection
- `broker_id`: Broker identifier
- `broker_url`: API endpoint URL
- `api_key`: Encrypted API key
- `api_secret`: Encrypted API secret
- `created_at`: Connection creation timestamp

### User Settings Table
- `id`: Auto-increment primary key
- `user_id`: Foreign key to users table
- `leverage`: Trading leverage (1-100)
- `position_size_percent`: Position size as percentage (0.01-1.0)
- `default_capital`: Default trading capital
- `max_capital_loss_percent`: Maximum loss percentage
- `created_at`: Settings creation timestamp
- `updated_at`: Last update timestamp

### Strategy Configs Table
- `id`: Auto-increment primary key
- `user_id`: Foreign key to users table
- `strategy_name`: Strategy identifier
- `broker_connection_id`: Foreign key to broker connections
- `is_active`: Whether strategy is running
- `config_data`: JSON configuration data
- `created_at`: Config creation timestamp
- `updated_at`: Last update timestamp

## API Endpoints

### Authentication
- `GET /` - Redirect to dashboard if authenticated, otherwise login
- `GET /login` - Login page
- `GET /google-login` - Initiate Google OAuth flow
- `GET /callback` - Google OAuth callback
- `GET /logout` - Logout user

### User Management
- `GET /api/user/profile` - Get current user profile
- `GET /api/user/settings` - Get user settings
- `POST /api/user/settings` - Update user settings

### Broker Management
- `GET /api/broker-connections` - List user's broker connections
- `POST /api/broker-connections` - Create new broker connection

### Strategy Management
- `GET /api/strategy/supertrend/status` - Get SuperTrend strategy status
- `POST /api/strategy/supertrend/toggle` - Start/stop SuperTrend strategy

### Market Data
- `GET /api/market/prices` - Get current market prices

## Dashboard Features

### Broker Connections Section
- Blue rounded rectangular cards
- Broker logo, name, and exchange
- Total P&L and wallet balance
- Maximum 3 cards per row

### Market Updates Section
- Grey bordered rectangular boxes
- Crypto symbols: BTC, ETH, SOL, DOGE
- Current market prices
- Horizontal scrollable layout

### SuperTrend Strategy Panel
- Live/Stopped status indicator
- Toggle switch for start/stop
- P&L display
- Configuration form
- Collapsible logs section

## Mobile Responsiveness

- Hamburger menu for mobile devices
- Responsive grid layouts
- Touch-friendly interface
- Optimized for various screen sizes

## Security Features

- Google OAuth 2.0 authentication
- Session management with Flask-Login
- API key encryption in database
- Rate limiting on API endpoints
- CORS configuration for production

## Development Notes

- The application creates a `users.db` SQLite database automatically
- Google OAuth credentials are required for full functionality
- Mock data is used for market prices in development
- Strategy execution integration with `strategy_st.py` needs to be implemented

## Production Deployment

For production deployment:

1. Set proper environment variables
2. Use a production WSGI server (Gunicorn)
3. Configure HTTPS
4. Set up proper database (PostgreSQL recommended)
5. Configure logging
6. Set up monitoring and alerts

## Troubleshooting

### Common Issues

1. **Google OAuth not working**: Check client ID, secret, and redirect URI
2. **Database errors**: Ensure write permissions in application directory
3. **Import errors**: Verify all dependencies are installed
4. **Port conflicts**: Change port in app.py if 5000 is in use

### Logs

Check the console output for error messages and debugging information.
