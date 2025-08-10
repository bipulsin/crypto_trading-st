# Development Workflow for Trade Manthan

This document outlines the new automated development workflow for the Trade Manthan application.

## 🎯 **Workflow Overview**

1. **Local Development** - All fixes and changes are made locally
2. **GitHub Push** - Changes are committed and pushed to GitHub
3. **Automated Deployment** - GitHub Actions automatically deploys to EC2
4. **Automated Testing** - Post-deployment tests run automatically

## 🚀 **Quick Start**

### Prerequisites

1. **Git Repository Setup**
   - Ensure your local repository is connected to GitHub
   - Set up proper branch structure (main/develop)

2. **GitHub Secrets Configuration**
   Add these secrets to your GitHub repository:
   - `EC2_HOST`: Your EC2 instance IP (e.g., `13.115.183.85`)
   - `EC2_USER`: EC2 user (e.g., `ubuntu`)
   - `PRIVATE_KEY`: Your EC2 private key content

### Local Development Workflow

#### 1. Make Changes Locally
```bash
# Make your changes to the code
# Edit files as needed
```

#### 2. Run Local Tests
```bash
# Test your changes locally
./dev_workflow.sh test
```

#### 3. Prepare for Deployment
```bash
# This will run tests and check git status
./dev_workflow.sh prepare
```

#### 4. Deploy Changes
```bash
# Full deployment workflow (prepare + commit + push)
./dev_workflow.sh deploy "Your commit message here"
```

## 📁 **File Structure**

```
crypto_trading_1/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── tests/
│   └── test_app.py            # Automated tests
├── dev_workflow.sh            # Local development script
├── app.py                     # Main Flask application
├── strategy_manager.py        # Strategy management
├── strategy_st.py            # SuperTrend strategy
└── DEVELOPMENT_WORKFLOW.md   # This file
```

## 🔧 **Development Scripts**

### `dev_workflow.sh`

A comprehensive script that handles local development, testing, and deployment preparation.

#### Usage:
```bash
# Run local tests
./dev_workflow.sh test

# Prepare for deployment (run tests, check git status)
./dev_workflow.sh prepare

# Commit and push changes
./dev_workflow.sh commit "Your commit message"

# Full deployment workflow
./dev_workflow.sh deploy "Your commit message"

# Check deployment status
./dev_workflow.sh status

# Show help
./dev_workflow.sh help
```

### `tests/test_app.py`

Automated tests that run before deployment to ensure code quality.

#### Running Tests:
```bash
# Run all tests
python3 tests/test_app.py

# Run specific test class
python3 -m unittest tests.test_app.TestTradeManthanApp
```

## 🔄 **GitHub Actions Workflow**

### Automated Deployment Process

1. **Trigger**: Push to `main` branch
2. **Testing**: Run local tests and code quality checks
3. **Deployment**: Automatically deploy to EC2
4. **Post-Deployment Testing**: Verify application health
5. **Notification**: Report deployment status

### Workflow Steps

1. **Test Job**
   - Checkout code
   - Set up Python environment
   - Install dependencies
   - Run tests
   - Check code quality

2. **Deploy Job** (only on main branch)
   - Deploy to EC2
   - Update dependencies
   - Restart services
   - Run post-deployment tests

## 🧪 **Testing Strategy**

### Local Testing
- Python syntax validation
- Module import testing
- Database operations testing
- Configuration validation

### Automated Testing
- Application health checks
- Strategy endpoint testing
- Nginx configuration validation
- Service status verification

## 📊 **Monitoring and Logs**

### GitHub Actions Logs
- View deployment progress at: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`

### EC2 Application Logs
```bash
# Check application logs
ssh -i your-key.pem ubuntu@your-ec2-ip "sudo journalctl -u trade-manthan-web -f"

# Check strategy manager logs
ssh -i your-key.pem ubuntu@your-ec2-ip "tail -f /home/ubuntu/trade_manthan_web/strategy_manager.log"
```

## 🚨 **Troubleshooting**

### Common Issues

1. **Deployment Fails**
   - Check GitHub Actions logs
   - Verify EC2 secrets are configured
   - Ensure EC2 instance is running

2. **Tests Fail**
   - Run tests locally first: `./dev_workflow.sh test`
   - Check for syntax errors
   - Verify dependencies are installed

3. **Application Not Responding**
   - Check service status: `sudo systemctl status trade-manthan-web`
   - Check nginx configuration: `sudo nginx -t`
   - Review application logs

### Rollback Procedure

If deployment fails, you can rollback:

1. **Check backup files** on EC2:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip "ls -la /home/ubuntu/trade_manthan_web/*.backup*"
```

2. **Restore from backup**:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip "sudo cp /home/ubuntu/trade_manthan_web/app.py.backup.YYYYMMDD_HHMMSS /home/ubuntu/trade_manthan_web/app.py"
```

## 📝 **Best Practices**

1. **Always test locally** before pushing
2. **Use descriptive commit messages**
3. **Check GitHub Actions logs** after deployment
4. **Monitor application logs** for issues
5. **Keep dependencies updated**

## 🔗 **Useful Commands**

```bash
# Check git status
git status

# View recent commits
git log --oneline -10

# Check remote repository
git remote -v

# Switch branches
git checkout main

# Pull latest changes
git pull origin main

# View deployment status
./dev_workflow.sh status
```

## 📞 **Support**

For issues or questions:
1. Check GitHub Actions logs first
2. Review this documentation
3. Check EC2 application logs
4. Verify configuration settings

---

**Last Updated**: December 2024
**Version**: 1.0
