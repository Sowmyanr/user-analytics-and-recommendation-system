# Punjab Rozgar Portal - Backend Setup Guide

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Copy the example environment file
   copy .env.example .env   # Windows
   cp .env.example .env     # Linux/Mac
   
   # Edit .env file with your settings
   # At minimum, change the SECRET_KEY for security
   ```

5. **Start the development server:**
   ```bash
   # Option 1: Using uvicorn directly
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

   # Option 2: Using Python module
   python -m app.main

   # Option 3: Using the startup script
   python run.py
   ```

### API Documentation

Once the server is running, visit:
- **Interactive API docs:** http://localhost:8000/api/docs
- **Alternative docs:** http://localhost:8000/api/redoc
- **Health check:** http://localhost:8000/health

### API Endpoints Overview

#### Authentication (`/api/v1/auth`)
- `POST /register` - User registration
- `POST /login` - User login
- `POST /logout` - User logout
- `GET /me` - Get current user

#### Analytics (`/api/v1/analytics`)
- `POST /track` - Track custom events
- `POST /track/pageview` - Track page views
- `GET /dashboard/realtime` - Real-time analytics
- `GET /dashboard/overview` - Dashboard overview
- `GET /reports/user-behavior` - User behavior reports

#### Jobs (`/api/v1/jobs`)
- `GET /` - List jobs with filters
- `POST /` - Create job posting
- `GET /{job_id}` - Get job details
- `POST /{job_id}/apply` - Apply to job
- `GET /my/applications` - User's applications

#### Users (`/api/v1/users`)
- `GET /me` - Get user profile
- `PUT /me` - Update user profile
- `GET /me/stats` - User statistics
- `POST /me/change-password` - Change password

#### Admin (`/api/v1/admin`)
- `GET /stats` - System statistics
- `GET /users` - Manage users
- `GET /jobs` - Manage jobs
- `GET /actions` - Admin action log

### Database

The application uses SQLite by default for development. The database file will be created automatically as `punjab_rozgar.db` in the backend directory.

### Analytics Features

The backend includes a comprehensive analytics system similar to Mixpanel/Google Analytics:

- **Event Tracking:** Track custom events, page views, user actions
- **Real-time Dashboard:** Live user activity, page views, events
- **User Behavior Analysis:** User journeys, session tracking, conversion funnels
- **Job Analytics:** Job view tracking, application analytics
- **Admin Statistics:** System overview, user growth, job statistics

### Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in your `.env` file
2. Use a production database (PostgreSQL recommended)
3. Set strong `SECRET_KEY`
4. Configure proper `ALLOWED_HOSTS`
5. Use a production ASGI server like gunicorn:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

### Development Features

- **Auto-reload:** Code changes trigger automatic server restart
- **API Documentation:** Interactive Swagger UI
- **Error Handling:** Comprehensive error tracking and logging
- **Security:** Rate limiting, security headers, CORS protection
- **Analytics Middleware:** Automatic API usage tracking

### Troubleshooting

1. **Import Errors:** Make sure you're in the backend directory and virtual environment is activated
2. **Port Issues:** Change the port in `.env` file or use `--port` flag
3. **Database Issues:** Delete `punjab_rozgar.db` to reset the database
4. **Package Issues:** Try `pip install --upgrade -r requirements.txt`

### Testing

Run tests with:
```bash
pytest
```

For coverage report:
```bash
pytest --cov=app
```
