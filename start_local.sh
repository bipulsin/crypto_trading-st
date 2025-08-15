#!/bin/bash
# Start Trade Manthan Web Application Locally

echo "🚀 Starting Trade Manthan Web Application..."
echo "============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Please create .env file with your API credentials"
    echo "   Example:"
    echo "   API_KEY=your_api_key"
    echo "   API_SECRET=your_api_secret"
    echo "   GOOGLE_CLIENT_ID=your_google_client_id"
    echo "   GOOGLE_CLIENT_SECRET=your_google_client_secret"
    echo ""
fi

# Start the application
echo "🌐 Starting Flask web application..."
echo "   Access at: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

python app.py


