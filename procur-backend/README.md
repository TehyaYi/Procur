# Procur GPO Platform - Backend

A modern, production-ready FastAPI backend for the Procur Group Purchasing Organization platform, optimized for React frontend integration.

## 🚀 Quick Start

### Option 1: Automated Setup
```bash
# Clone or create the project directory
mkdir procur-backend && cd procur-backend

# Copy all files from the artifacts into this directory structure
# (See "File Structure" section below)

# Run the setup script
chmod +x setup.sh
./setup.sh

# Configure your environment
cp .env.example .env
# Edit .env with your Firebase and SMTP settings

# Add your Firebase service account key
# Download from Firebase Console → Project Settings → Service Accounts
# Save as: firebase-service-account-key.json

# Run the development server
source venv/bin/activate
uvicorn procur.main:app --reload
```

### Option 2: Manual Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p uploads/users uploads/groups logs

# Copy environment file
cp .env.example .env

# Edit configuration
nano .env

# Run server
uvicorn procur.main:app --reload
```

## 📁 File Structure

```
procur-backend/
├── procur/                     # Main Python package
│   ├── main.py                # FastAPI application
│   ├── core/                  # Core modules
│   │   ├── config.py         # Settings & configuration
│   │   ├── firebase.py       # Firebase integration
│   │   ├── dependencies.py   # Auth dependencies
│   │   └── ...
│   ├── api/routes/           # API endpoints
│   │   ├── auth.py          # Authentication
│   │   ├── users.py         # User management
│   │   ├── groups.py        # Group operations
│   │   └── ...
│   ├── models/              # Data models
│   ├── services/            # Business logic
│   └── templates/           # Email templates
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── docker-compose.yml      # Docker setup
└── setup.sh               # Automated setup
```

## ⚙️ Configuration

### Required Environment Variables
```bash
# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-service-account-key.json
FIREBASE_PROJECT_ID=your-firebase-project-id

# Email (Gmail recommended for development)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM_EMAIL=noreply@yourdomain.com

# Security
SECRET_KEY=your-secure-secret-key-min-32-chars

# React Frontend
FRONTEND_URL=http://localhost:3000
```

### Firebase Setup
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a new project or select existing
3. Go to Project Settings → Service Accounts
4. Generate new private key
5. Save as `firebase-service-account-key.json` in project root

### Gmail App Password Setup
1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account Settings → Security → App Passwords
3. Generate app password for "Mail"
4. Use this password in `SMTP_PASSWORD` (not your regular password)

## 🐳 Docker Deployment

### Development
```bash
# Start Redis for development
docker-compose --profile development up redis-dev
```

### Production
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d
```

## 🧪 Testing

```bash
# Install test dependencies (included in requirements.txt)
pytest

# Run with coverage
pytest --cov=procur

# Run specific test file
pytest procur/tests/test_auth.py
```

## 📡 API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/api/docs
- **ReDoc Documentation**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

## 🔌 React Integration

### API Base URL
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### Authentication Headers
```javascript
const headers = {
  'Authorization': `Bearer ${firebaseIdToken}`,
  'Content-Type': 'application/json'
};
```

### Example API Calls
```javascript
// Get user groups
const response = await fetch(`${API_BASE_URL}/api/groups`, {
  headers: {
    'Authorization': `Bearer ${idToken}`
  }
});
const data = await response.json();
```

## 📊 Features

### Authentication & Users
- ✅ Firebase ID token verification
- ✅ User registration and profile management
- ✅ Role-based access control (Admin/Member/Curator)
- ✅ Avatar upload support

### Group Management
- ✅ Create/update/delete groups
- ✅ Public/private/invite-only privacy settings
- ✅ Member management with admin controls
- ✅ Group logo and banner uploads

### Join Requests
- ✅ Request to join groups
- ✅ Admin approval workflow
- ✅ Email notifications to admins
- ✅ Automatic member addition on approval

### Invitations
- ✅ Generate shareable invitation links
- ✅ Time-limited and usage-limited invitations
- ✅ Bulk email invitations with beautiful templates
- ✅ Token-based validation

### File Uploads
- ✅ User avatars and group logos
- ✅ File validation and size limits
- ✅ CDN integration ready
- ✅ Secure file handling

### Production Features
- ✅ Rate limiting with Redis
- ✅ Comprehensive logging
- ✅ Health checks for monitoring
- ✅ Docker containerization
- ✅ Nginx reverse proxy configuration
- ✅ CORS configured for React

## 🔧 Development

### Project Structure
The backend follows a clean architecture pattern:
- **Core**: Configuration, Firebase, dependencies
- **Models**: Pydantic schemas for data validation
- **API**: FastAPI routers for different resources
- **Services**: Business logic and external integrations
- **Templates**: Email templates and static content

### Adding New Features
1. Define schemas in `models/schemas.py`
2. Create service logic in `services/`
3. Add API endpoints in `api/routes/`
4. Write tests in `tests/`

### Code Quality
```bash
# Format code
black procur/

# Sort imports
isort procur/

# Lint code
flake8 procur/

# Type checking
mypy procur/
```

## 🚨 Troubleshooting

### Common Issues

**Firebase Authentication Error**
- Ensure `firebase-service-account-key.json` exists
- Check `FIREBASE_PROJECT_ID` is correct
- Verify Firebase project has Authentication enabled

**Email Not Sending**
- Use Gmail App Password, not regular password
- Enable 2-Factor Authentication first
- Check SMTP settings in `.env`

**Rate Limiting Issues**
- Set `ENABLE_RATE_LIMITING=False` for development
- Check Redis connection if enabled

**File Upload Errors**
- Ensure `uploads/` directory exists and is writable
- Check `MAX_FILE_SIZE` setting
- Verify file type is in `ALLOWED_FILE_TYPES`

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support, email support@procur.app or join our community Discord.
