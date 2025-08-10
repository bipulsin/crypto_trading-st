#!/bin/bash

# Remote strategy restart script for EC2
echo "🔄 Restarting strategy on EC2 server..."

# EC2 connection details
EC2_HOST="13.115.183.85"
EC2_USER="ubuntu"
EC2_KEY="trademanthan.pem"

# Check if key file exists
if [ ! -f "$EC2_KEY" ]; then
    echo "❌ Error: EC2 key file $EC2_KEY not found"
    exit 1
fi

# Make key file readable only by owner
chmod 400 "$EC2_KEY"

echo "📡 Connecting to EC2 server: $EC2_USER@$EC2_HOST"

# SSH into EC2 and restart the strategy
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" << 'EOF'
    echo "🖥️  Connected to EC2 server"
    
    # Navigate to the deployment directory
    cd deploy_package
    
    # Check if the directory exists
    if [ ! -d "deploy_package" ]; then
        echo "📁 Creating deploy_package directory..."
        mkdir -p deploy_package
        cd deploy_package
    fi
    
    # Check if strategy files exist
    if [ ! -f "strategy_st.py" ]; then
        echo "📥 Downloading latest code from GitHub..."
        git clone https://github.com/bipulsin/crypto_trading-st.git temp_repo
        cp -r temp_repo/* .
        rm -rf temp_repo
    fi
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "🐍 Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Stop any existing strategy processes
    echo "🛑 Stopping existing strategy processes..."
    pkill -f "strategy_st.py" || true
    pkill -f "python3.*strategy" || true
    
    # Wait a moment for processes to stop
    sleep 2
    
    # Start the strategy
    echo "🚀 Starting SuperTrend strategy..."
    nohup python3 strategy_st.py > strategy.log 2>&1 &
    
    # Get the process ID
    STRATEGY_PID=$!
    echo "📝 Strategy started with PID: $STRATEGY_PID"
    
    # Wait a moment and check if it's running
    sleep 3
    if ps -p $STRATEGY_PID > /dev/null; then
        echo "✅ Strategy is running successfully"
        echo "📊 Process ID: $STRATEGY_PID"
        echo "📋 Log file: strategy.log"
    else
        echo "❌ Strategy failed to start"
        echo "📋 Checking logs..."
        tail -20 strategy.log
        exit 1
    fi
    
    # Show recent logs
    echo "📋 Recent strategy logs:"
    tail -10 strategy.log
    
    echo "🎯 Strategy restart completed successfully!"
EOF

if [ $? -eq 0 ]; then
    echo "✅ Strategy restarted successfully on EC2"
    echo "🎯 The SuperTrend strategy is now running with the fixes deployed."
    echo "📊 Monitor the strategy on EC2 using: ssh -i $EC2_KEY $EC2_USER@$EC2_HOST"
    echo "📋 View logs: ssh -i $EC2_KEY $EC2_USER@$EC2_HOST 'cd deploy_package && tail -f strategy.log'"
else
    echo "❌ Failed to restart strategy on EC2"
    exit 1
fi
