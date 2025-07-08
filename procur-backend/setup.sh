#!/bin/bash

# =============================================================================
# PROCUR SETUP SCRIPT
# =============================================================================
# This script helps you set up the Procur backend quickly

set -e

echo "🚀 Setting up Procur GPO Platform..."

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [[ $(echo "$python_version >= 3.11" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.11+ is required. You have Python $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads/users uploads/groups logs

# Copy environment file
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
else
    echo "✅ Environment file already exists"
fi

# Create __init__.py files
echo "🐍 Creating Python package files..."
touch procur/__init__.py
touch procur/core/__init__.py
touch procur/models/__init__.py
touch procur/api/__init__.py
touch procur/api/routes/__init__.py
touch procur/services/__init__.py
touch procur/templates/__init__.py
touch procur/tests/__init__.py

# Set proper permissions
chmod +x setup.sh
chmod 755 uploads/

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Firebase and SMTP configuration"
echo "2. Add your Firebase service account key as 'firebase-service-account-key.json'"
echo "3. Run the development server:"
echo "   source venv/bin/activate"
echo "   uvicorn procur.main:app --reload"
echo ""
echo "4. Visit http://localhost:8000/api/docs for API documentation"
echo ""
echo "For production deployment:"
echo "   docker-compose up --build"
echo ""

# Check if Firebase key exists
if [ ! -f "firebase-service-account-key.json" ]; then
    echo "⚠️  Don't forget to add your Firebase service account key!"
fi

echo "Happy coding! 🚀"
