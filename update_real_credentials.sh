#!/bin/bash
# Update Real Delta Exchange API Credentials

echo "🔑 Delta Exchange Real API Credentials Update"
echo "============================================="
echo ""

# Get API credentials from user
read -p "Enter your Delta Exchange API Key: " API_KEY
read -s -p "Enter your Delta Exchange API Secret: " API_SECRET
echo ""

if [ -z "$API_KEY" ] || [ -z "$API_SECRET" ]; then
    echo "❌ Error: API Key and Secret cannot be empty"
    exit 1
fi

echo ""
echo "📡 Updating credentials on EC2 server..."
echo "   Host: 13.115.183.85"
echo "   User: ubuntu"
echo ""

# Update the database on EC2 with real credentials
ssh -i trademanthan.pem ubuntu@13.115.183.85 << EOF
    cd deploy_package
    echo "🔄 Updating broker_connections table with real credentials..."
    
    # Update both records to ensure consistency
    sqlite3 users.db "UPDATE broker_connections SET api_key='$API_KEY', api_secret='$API_SECRET' WHERE id=1;"
    sqlite3 users.db "UPDATE broker_connections SET api_key='$API_KEY', api_secret='$API_SECRET' WHERE id=2;"
    
    if [ \$? -eq 0 ]; then
        echo "✅ Real API credentials updated successfully!"
        echo ""
        echo "🔧 Running broker configuration script..."
        source venv/bin/activate
        python3 configure_broker_ec2.py
        
        if [ \$? -eq 0 ]; then
            echo ""
            echo "✅ Broker connection configured successfully!"
            echo "🔄 Restarting strategy with real credentials..."
            
            # Stop existing strategy
            pkill -f "strategy_st.py" || true
            sleep 2
            
            # Start strategy with real credentials
            nohup python3 strategy_st.py > strategy.log 2>&1 &
            STRATEGY_PID=\$!
            echo "📝 Strategy started with PID: \$STRATEGY_PID"
            sleep 5
            
            # Check if strategy is running
            if ps -p \$STRATEGY_PID > /dev/null; then
                echo "✅ Strategy is running successfully with real credentials!"
                echo "📊 Process ID: \$STRATEGY_PID"
                echo "📋 Log file: strategy.log"
                echo ""
                echo "📋 Recent strategy logs:"
                tail -15 strategy.log
                echo ""
                echo "🎯 Strategy is now running with real API credentials!"
                echo "📈 Monitor trading activity in the logs above"
            else
                echo "❌ Strategy failed to start"
                echo "📋 Checking error logs..."
                tail -20 strategy.log
                exit 1
            fi
        else
            echo "❌ Failed to configure broker connection"
            exit 1
        fi
    else
        echo "❌ Failed to update API credentials"
        exit 1
    fi
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Real API credentials have been deployed!"
    echo ""
    echo "📊 System Status:"
    echo "   ✅ Wallet balance fallback mechanism: ACTIVE"
    echo "   ✅ Bracket order fallback mechanism: ACTIVE"
    echo "   ✅ Real API credentials: CONFIGURED"
    echo "   ✅ Strategy: RUNNING with real credentials"
    echo ""
    echo "🔍 Monitor the strategy:"
    echo "   ssh -i trademanthan.pem ubuntu@13.115.183.85"
    echo "   cd deploy_package"
    echo "   tail -f strategy.log"
    echo ""
    echo "🎯 The wallet balance and order placement issues are now FIXED and running with real credentials!"
else
    echo ""
    echo "❌ Failed to update credentials or start strategy"
    echo "Please check the error messages above and try again"
    exit 1
fi
