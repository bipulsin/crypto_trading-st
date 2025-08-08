#!/bin/bash

# Update Dashboard with Trade Manthan Header and Logo
# This script updates the web configuration dashboard on EC2

set -e

echo "🎨 Updating Dashboard with Trade Manthan Header..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
EC2_IP="13.115.183.85"
EC2_USER="ubuntu"
KEY_FILE="trademanthan.pem"

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    print_error "Key file $KEY_FILE not found!"
    print_warning "Please update the KEY_FILE variable in this script with your actual key file path."
    exit 1
fi

print_status "Connecting to EC2 instance at $EC2_IP..."

# SSH into EC2 and update the dashboard
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" << 'EOF'

echo "🎨 Updating dashboard with Trade Manthan header..."

# Navigate to project directory
cd /home/ubuntu/crypto_trading-st

# Create static directory if it doesn't exist
echo "📁 Creating static directory..."
mkdir -p static

# Copy logo to static directory
echo "🖼️  Copying logo to static directory..."
if [ -f "logo.jpg" ]; then
    cp logo.jpg static/
    echo "✅ Logo copied successfully"
else
    echo "⚠️  Logo file not found, creating placeholder..."
    # Create a simple placeholder image using ImageMagick if available
    if command -v convert >/dev/null 2>&1; then
        convert -size 60x60 xc:transparent -fill '#667eea' -draw 'circle 30,30 30,5' static/logo.jpg
    else
        # Create a simple text file as placeholder
        echo "Logo placeholder" > static/logo.jpg
    fi
fi

# Update the HTML template with new header
echo "📝 Updating HTML template..."
cat > templates/config_dashboard.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trade Manthan - Trading Bot Configuration</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .config-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .form-control, .form-select {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            transition: all 0.3s ease;
        }
        .form-control:focus, .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            border-radius: 10px;
            padding: 10px 25px;
            font-weight: 600;
        }
        .section-header {
            color: #495057;
            font-weight: 700;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        .config-group {
            margin-bottom: 25px;
        }
        .help-text {
            font-size: 0.875rem;
            color: #6c757d;
            margin-top: 5px;
        }
        .header-section {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .header-logo {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }
        .header-title {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(45deg, #ffffff, #f8f9fa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .header-subtitle {
            color: rgba(255, 255, 255, 0.8);
            font-size: 1.1rem;
            font-weight: 300;
        }
    </style>
</head>
<body>
    <div class="container-fluid py-4">
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <!-- Header with Logo and Title -->
                <div class="header-section">
                    <div class="row align-items-center">
                        <div class="col-auto">
                            <img src="/static/logo.jpg" alt="Trade Manthan Logo" class="header-logo">
                        </div>
                        <div class="col">
                            <h1 class="header-title mb-2">Trade Manthan</h1>
                            <p class="header-subtitle mb-0">Advanced Trading Bot Configuration Dashboard</p>
                        </div>
                    </div>
                </div>

                <!-- Alerts -->
                <div id="alerts"></div>

                <!-- Configuration Form -->
                <div class="config-card p-4">
                    <form id="configForm">
                        <!-- Trading Configuration -->
                        <div class="config-group">
                            <h3 class="section-header">
                                <i class="fas fa-chart-line me-2"></i>Trading Configuration
                            </h3>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Leverage</label>
                                        <input type="number" class="form-control" name="LEVERAGE" min="1" max="100" step="1">
                                        <div class="help-text">Trading leverage (1-100x)</div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Position Size (%)</label>
                                        <input type="number" class="form-control" name="POSITION_SIZE_PERCENT" min="0.01" max="1.0" step="0.01">
                                        <div class="help-text">Percentage of balance to use per trade (0.01-1.0)</div>
                                    </div>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Take Profit Multiplier</label>
                                        <input type="number" class="form-control" name="TAKE_PROFIT_MULTIPLIER" min="0.1" max="10.0" step="0.1">
                                        <div class="help-text">Risk-reward ratio for take profit (0.1-10.0)</div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Trailing Stop</label>
                                        <select class="form-select" name="ST_WITH_TRAILING">
                                            <option value="true">Enabled</option>
                                            <option value="false">Disabled</option>
                                        </select>
                                        <div class="help-text">Enable trailing stop loss for SuperTrend strategy</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- SuperTrend Parameters -->
                        <div class="config-group">
                            <h3 class="section-header">
                                <i class="fas fa-wave-square me-2"></i>SuperTrend Parameters
                            </h3>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">SuperTrend Period</label>
                                        <input type="number" class="form-control" name="SUPERTREND_PERIOD" min="1" max="50" step="1">
                                        <div class="help-text">Lookback period for SuperTrend calculation (1-50)</div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">SuperTrend Multiplier</label>
                                        <input type="number" class="form-control" name="SUPERTREND_MULTIPLIER" min="0.1" max="10.0" step="0.1">
                                        <div class="help-text">ATR multiplier for SuperTrend (0.1-10.0)</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Risk Management -->
                        <div class="config-group">
                            <h3 class="section-header">
                                <i class="fas fa-shield-alt me-2"></i>Risk Management
                            </h3>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Max Capital Loss (%)</label>
                                        <input type="number" class="form-control" name="MAX_CAPITAL_LOSS_PERCENT" min="0.01" max="100" step="0.01">
                                        <div class="help-text">Maximum capital loss percentage (0.01-100)</div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Default Capital</label>
                                        <input type="number" class="form-control" name="DEFAULT_CAPITAL" min="0.01" step="0.01">
                                        <div class="help-text">Default capital amount for trading</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Order Management -->
                        <div class="config-group">
                            <h3 class="section-header">
                                <i class="fas fa-list-alt me-2"></i>Order Management
                            </h3>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label class="form-label">Respect Existing Orders</label>
                                        <select class="form-select" name="RESPECT_EXISTING_ORDERS">
                                            <option value="true">Yes</option>
                                            <option value="false">No</option>
                                        </select>
                                        <div class="help-text">Check for existing orders before placing new ones</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Action Buttons -->
                        <div class="text-center mt-4">
                            <button type="submit" class="btn btn-primary btn-lg me-3">
                                <i class="fas fa-save me-2"></i>Save Configuration
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-lg" onclick="loadConfig()">
                                <i class="fas fa-refresh me-2"></i>Reload
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Load configuration on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadConfig();
        });

        // Load configuration from server
        function loadConfig() {
            fetch('/api/config')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        populateForm(data.config);
                        showAlert('Configuration loaded successfully!', 'success');
                    } else {
                        showAlert('Failed to load configuration: ' + data.error, 'danger');
                    }
                })
                .catch(error => {
                    showAlert('Error loading configuration: ' + error.message, 'danger');
                });
        }

        // Populate form with configuration data
        function populateForm(config) {
            Object.keys(config).forEach(key => {
                const element = document.querySelector(`[name="${key}"]`);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = config[key];
                    } else {
                        element.value = config[key];
                    }
                }
            });
        }

        // Handle form submission
        document.getElementById('configForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const config = {};
            
            for (let [key, value] of formData.entries()) {
                // Convert string values to appropriate types
                if (value === 'true') config[key] = true;
                else if (value === 'false') config[key] = false;
                else if (!isNaN(value) && value !== '') config[key] = parseFloat(value);
                else config[key] = value;
            }

            // Validate configuration
            fetch('/api/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.valid) {
                    // Save configuration
                    return fetch('/api/config', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(config)
                    });
                } else {
                    throw new Error(data.errors.join(', '));
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Configuration saved successfully!', 'success');
                } else {
                    showAlert('Failed to save configuration: ' + data.error, 'danger');
                }
            })
            .catch(error => {
                showAlert('Error: ' + error.message, 'danger');
            });
        });

        // Show alert message
        function showAlert(message, type) {
            const alertsDiv = document.getElementById('alerts');
            const alertHtml = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            alertsDiv.innerHTML = alertHtml;
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                const alert = alertsDiv.querySelector('.alert');
                if (alert) {
                    alert.remove();
                }
            }, 5000);
        }
    </script>
</body>
</html>
HTMLEOF

# Update web_config.py to serve static files
echo "🔧 Updating Flask app to serve static files..."
sed -i "s/app = Flask(__name__)/app = Flask(__name__, static_folder='static')/" web_config.py

# Restart the web service
echo "🔄 Restarting web service..."
sudo systemctl restart trading-bot-web-config

# Check service status
echo "📊 Checking service status..."
sudo systemctl status trading-bot-web-config --no-pager

# Test the dashboard
echo "🧪 Testing dashboard..."
sleep 3

if curl -s -k https://13.115.183.85 > /dev/null; then
    echo "✅ Dashboard updated successfully!"
else
    echo "❌ Dashboard update failed"
    echo "Checking service logs..."
    sudo journalctl -u trading-bot-web-config -n 10
fi

echo ""
echo "✅ Dashboard updated with Trade Manthan header!"
echo "================================================"
echo "🌐 Access your updated dashboard:"
echo "   HTTPS: https://13.115.183.85"
echo ""
echo "🎨 New Features:"
echo "   - Trade Manthan header with logo"
echo "   - Professional styling"
echo "   - Responsive design"
echo "================================================"

EOF

print_status "Dashboard updated successfully!"
print_status "You can now access your updated dashboard at: https://13.115.183.85" 