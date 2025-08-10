#!/bin/bash

# Deploy fixes for wallet balance and bracket order issues
echo "🚀 Deploying fixes for wallet balance and bracket order issues..."

# Check if we're in the right directory
if [ ! -f "strategy_st.py" ]; then
    echo "❌ Error: strategy_st.py not found. Please run this script from the project root."
    exit 1
fi

# Stage the modified files
echo "📁 Staging modified files..."
git add strategy_st.py delta_api.py

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "ℹ️  No changes to commit. Files may already be up to date."
else
    # Commit the changes
    echo "💾 Committing fixes..."
    git commit -m "Fix wallet balance fallback and bracket order error handling

- Add default_capital fallback when API returns None/0 balance
- Improve bracket order error handling with fallback to simple orders
- Better error logging and recovery mechanisms
- Fix duplicate code in trading logic"
    
    # Push to remote repository
    echo "📤 Pushing to remote repository..."
    git push origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pushed fixes to GitHub"
    else
        echo "❌ Failed to push to GitHub"
        exit 1
    fi
fi

# Deploy to EC2
echo "🖥️  Deploying to EC2 server..."
./deploy_to_ec2.sh

if [ $? -eq 0 ]; then
    echo "✅ Successfully deployed to EC2"
    
    # Restart the strategy
    echo "🔄 Restarting the strategy on EC2..."
    ./start_trade_manthan.sh
    
    if [ $? -eq 0 ]; then
        echo "✅ Strategy restarted successfully"
        echo "🎯 Fixes deployed and strategy restarted. Monitor logs for improvements."
    else
        echo "❌ Failed to restart strategy"
        exit 1
    fi
else
    echo "❌ Failed to deploy to EC2"
    exit 1
fi

echo "🎉 Deployment complete! The strategy should now handle wallet balance and bracket order issues gracefully."
