# Procur GPO Platform

A Group Purchasing Organization (GPO) platform built with FastAPI backend and React frontend, designed for vertical-specific buying groups.

## 🏗️ Architecture

- **Backend**: FastAPI with Python 3.8+
- **Frontend**: React 19 with TypeScript
- **Database**: Firebase Firestore
- **Cache**: Redis
- **Authentication**: Firebase Auth
- **File Storage**: Local file system with Nginx serving
- **Reverse Proxy**: Nginx (production)

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+** and npm
- **Docker** and Docker Compose (for Redis and production setup)
- **Firebase Project** with Firestore and Authentication enabled

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd procur
```

### 2. Backend Setup

#### Install Python Dependencies

```bash
cd procur-backend
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

pip install -r requirements.txt
```

#### Environment Configuration

Create a `.env` file in `procur-backend/`:

```bash
# App Configuration
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=true

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=./firebase-service-account-key.json
FIREBASE_PROJECT_ID=your-firebase-project-id

# Email Configuration
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

#### Firebase Setup

1. Download your Firebase service account key from Firebase Console
2. Place it as `firebase-service-account-key.json` in `procur-backend/`
3. Enable Firestore and Authentication in your Firebase project

#### Start Redis (Development)

```bash
# Using Docker
docker-compose --profile development up redis-dev

# Or install Redis locally
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

#### Run Backend

```bash
# Development mode
uvicorn procur.main:app --reload --host 0.0.0.0 --port 8000

# Or using the provided script
python run_tests.py
```

The API will be available at:
- **API**: http://localhost:8000/api
- **Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### 3. Frontend Setup

#### Install Dependencies

```bash
cd procur-frontend
npm install
```

#### Environment Configuration

Create a `.env` file in `procur-frontend/`:

```bash
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_FIREBASE_CONFIG={"apiKey":"your-api-key","authDomain":"your-project.firebaseapp.com","projectId":"your-project-id","storageBucket":"your-project.appspot.com","messagingSenderId":"123456789","appId":"your-app-id"}
```

#### Run Frontend

```bash
npm start
```

The React app will be available at: http://localhost:3000

## 🐳 Docker Setup (Production)

### Backend with Docker

```bash
cd procur-backend

# Build and run all services
docker-compose up --build

# Run only specific services
docker-compose up procur-api redis

# Run in background
docker-compose up -d
```

### Frontend Build

```bash
cd procur-frontend
npm run build
```

## 🧪 Testing

### Backend Tests

```bash
cd procur-backend

# Run all tests
pytest

# Run with coverage
pytest --cov=procur

# Run specific test file
pytest tests/test_api_endpoints.py
```

### Frontend Tests

```bash
cd procur-frontend

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage --watchAll=false
```

## 📁 Project Structure

```
procur/
├── procur-backend/          # FastAPI backend
│   ├── procur/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core configuration and middleware
│   │   ├── models/         # Data models and schemas
│   │   ├── services/       # Business logic services
│   │   └── main.py         # FastAPI application entry point
│   ├── requirements.txt     # Python dependencies
│   ├── docker-compose.yml  # Docker services configuration
│   └── Dockerfile          # Backend container definition
├── procur-frontend/         # React frontend
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API service layer
│   │   └── types/          # TypeScript type definitions
│   ├── package.json        # Node.js dependencies
│   └── tsconfig.json       # TypeScript configuration
└── README.md               # This file
```

## 🔧 Development Workflow

### 1. Start Development Environment

```bash
# Terminal 1: Start Redis
cd procur-backend
docker-compose --profile development up redis-dev

# Terminal 2: Start Backend
cd procur-backend
source venv/bin/activate
uvicorn procur.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start Frontend
cd procur-frontend
npm start
```

### 2. Code Quality

#### Backend
```bash
cd procur-backend

# Format code
black procur/
isort procur/

# Lint code
flake8 procur/
mypy procur/
```

#### Frontend
```bash
cd procur-frontend

# Lint and format (if using ESLint/Prettier)
npm run lint
npm run format
```

## 🚨 Common Issues

### Backend Issues

1. **Firebase Connection Error**
   - Verify `firebase-service-account-key.json` exists and is valid
   - Check Firebase project ID in `.env`

2. **Redis Connection Error**
   - Ensure Redis is running: `docker-compose --profile development up redis-dev`
   - Check Redis URL in `.env`

3. **Import Errors**
   - Activate virtual environment: `source venv/bin/activate`
   - Install dependencies: `pip install -r requirements.txt`

### Frontend Issues

1. **API Connection Error**
   - Verify backend is running on port 8000
   - Check `REACT_APP_API_URL` in `.env`

2. **Firebase Auth Error**
   - Verify Firebase config in `.env`
   - Enable Authentication in Firebase Console

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 🔐 Security Features

- JWT-based authentication
- Rate limiting
- CORS protection
- Security headers
- File upload validation
- Input sanitization

## 📊 Monitoring

- Structured logging with structlog
- Sentry integration for error tracking
- Health check endpoints
- Rate limiting metrics

## 🚀 Deployment

### Production Environment Variables

```bash
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=your-domain.com
FRONTEND_URL=https://your-domain.com
```

### Docker Production

```bash
cd procur-backend
docker-compose --profile production up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For development issues:
1. Check the logs in `procur-backend/logs/`
2. Verify environment configuration
3. Check Firebase Console for authentication issues
4. Review API documentation at `/api/docs`

---

**Happy coding! 🎉**
