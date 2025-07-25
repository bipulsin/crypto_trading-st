#!/bin/bash

# Set your project directory here
PROJECT_DIR=~/crypto_trading-st

# Set your GitHub repo URL here
GITHUB_REPO="https://github.com/bipulsin/crypto_trading-st.git"

# Go to the project directory
cd "$PROJECT_DIR" || { echo "Directory $PROJECT_DIR not found!"; exit 1; }

# Initialize git if not already a repo
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    git remote add origin "$GITHUB_REPO"
else
    echo "Git repository already initialized."
    git remote set-url origin "$GITHUB_REPO"
fi

# Fetch latest from GitHub and reset local code to match remote
echo "Fetching latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# (Optional) Clean untracked files and directories
# Uncomment the next line if you want to remove files not tracked by git
# git clean -fd

# (Optional) Install/update Python dependencies
if [ -f requirements.txt ]; then
    echo "Installing/updating Python dependencies..."
    pip install -r requirements.txt
fi

echo "Update complete!"
