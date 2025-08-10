#!/bin/bash

# Development Workflow Script for Trade Manthan
# This script handles local development, testing, and preparation for deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository. Please navigate to the project directory."
        exit 1
    fi
}

# Function to check if there are uncommitted changes
check_uncommitted_changes() {
    if ! git diff-index --quiet HEAD --; then
        print_warning "You have uncommitted changes. Please commit or stash them before proceeding."
        echo "Uncommitted files:"
        git diff --name-only
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Function to run local tests
run_local_tests() {
    print_status "Running local tests..."
    
    # Check Python syntax
    python3 -m py_compile app.py strategy_manager.py strategy_st.py
    print_success "Syntax check passed"
    
    # Check imports
    python3 -c "import app; print('✅ App imports successfully')"
    python3 -c "import strategy_manager; print('✅ Strategy manager imports successfully')"
    python3 -c "import strategy_st; print('✅ Strategy ST imports successfully')"
    
    # Check for TODO/FIXME items
    if grep -r "TODO\|FIXME\|XXX" . --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__; then
        print_warning "Found TODO/FIXME items - please address them before deployment"
    else
        print_success "No TODO/FIXME items found"
    fi
    
    print_success "Local tests completed"
}

# Function to prepare for deployment
prepare_deployment() {
    print_status "Preparing for deployment..."
    
    # Check if we're on main branch
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        print_warning "You're not on the main branch. Current branch: $CURRENT_BRANCH"
        read -p "Do you want to switch to main branch? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git checkout main
        fi
    fi
    
    # Pull latest changes
    print_status "Pulling latest changes from remote..."
    git pull origin main
    
    # Run tests
    run_local_tests
}

# Function to commit and push changes
commit_and_push() {
    print_status "Committing and pushing changes..."
    
    # Get commit message
    if [ -z "$1" ]; then
        read -p "Enter commit message: " COMMIT_MESSAGE
    else
        COMMIT_MESSAGE="$1"
    fi
    
    # Add all changes
    git add .
    
    # Commit changes
    git commit -m "$COMMIT_MESSAGE"
    
    # Push to remote
    git push origin main
    
    print_success "Changes committed and pushed successfully"
}

# Function to show deployment status
show_deployment_status() {
    print_status "Checking deployment status..."
    
    # Wait for GitHub Actions to complete (this is a basic check)
    echo "⏳ Waiting for GitHub Actions to start..."
    sleep 5
    
    print_warning "Please check GitHub Actions at: https://github.com/YOUR_USERNAME/YOUR_REPO/actions"
    print_status "Deployment typically takes 2-3 minutes to complete"
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  test           Run local tests"
    echo "  prepare        Prepare for deployment (run tests, check git status)"
    echo "  commit [MSG]   Commit and push changes (optional commit message)"
    echo "  deploy [MSG]   Full deployment workflow (prepare + commit + push)"
    echo "  status         Show deployment status"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 test                    # Run local tests only"
    echo "  $0 prepare                 # Check everything before deployment"
    echo "  $0 commit 'Fix strategy toggle'  # Commit with message"
    echo "  $0 deploy 'Update strategy manager'  # Full deployment workflow"
}

# Main script logic
case "${1:-help}" in
    test)
        check_git_repo
        run_local_tests
        ;;
    prepare)
        check_git_repo
        check_uncommitted_changes
        prepare_deployment
        ;;
    commit)
        check_git_repo
        commit_and_push "$2"
        ;;
    deploy)
        check_git_repo
        check_uncommitted_changes
        prepare_deployment
        commit_and_push "$2"
        show_deployment_status
        ;;
    status)
        show_deployment_status
        ;;
    help|*)
        show_help
        ;;
esac
