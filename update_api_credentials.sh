#!/bin/bash
# Update API Credentials on EC2

echo "🔑 Delta Exchange API Credentials Update"
echo "========================================"
echo ""

# Get API credentials from user
read -p "Enter your Delta Exchange API Key: " API_KEY
read -s -p "Enter your Delta Exchange API Secret: " API_SECRET
echo ""

if [ -z "$API_KEY" ] || [ -z "$API_SECRET" ]; then
    echo "❌ Error: API Key and Secret cannot be empty"
    exit 1
fi

echo "📡 Updating credentials on EC2 server..."
echo "   Host: 13.115.183.85"
echo "   User: ubuntu"
echo ""

# Update the database on EC2
ssh -i trademanthan.pem ubuntu@13.115.183.85 << EOF
    cd deploy_package
    echo "Updating broker_connections table..."
    sqlite3 users.db "UPDATE broker_connections SET api_key='$API_KEY', api_secret='$API_SECRET' WHERE id=1;"
    
    if [ \$? -eq 0 ]; then
        echo "✅ API credentials updated successfully!"
        echo "Running broker configuration script..."
        source venv/bin/activate
        python3 configure_broker_ec2.py
        
        if [ \$? -eq 0 ]; then
            echo "✅ Broker connection configured successfully!"
            echo "Restarting strategy..."
            pkill -f "strategy_st.py" || true
            sleep 2
            nohup python3 strategy_st.py > strategy.log 2>&1 &
            STRATEGY_PID=\$!
            echo "📝 Strategy started with PID: \$STRATEGY_PID"
            sleep 3
            
            if ps -p \$STRATEGY_PID > /dev/null; then
                echo "✅ Strategy is running successfully!"
                echo "📊 Process ID: \$STRATEGY_PID"
                echo "📋 Log file: strategy.log"
                echo ""
                echo "📋 Recent strategy logs:"
                tail -10 strategy.log
            else
                echo "❌ Strategy failed to start"
                echo "📋 Checking logs..."
                tail -20 strategy.log
            fi
        else
            echo "❌ Failed to configure broker connection"
        fi
    else
        echo "❌ Failed to update API credentials"
    fi
EOF

echo ""
echo "🎯 API credentials update completed!"
echo "📊 Monitor the strategy on EC2 using: ssh -i trademanthan.pem ubuntu@13.115.183.85"
echo "📋 View logs: ssh -i trademanthan.pem ubuntu@13.115.183.85 'cd deploy_package && tail -f strategy.log'"
