# DairyMitra Deployment Guide

## 1. Local Development Setup

### Backend (Python Flask)
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate # Linux/Mac
pip install -r requirements.txt
cp ../.env.example .env
# Configure your .env variables
flask db upgrade
python run.py
```

### Mobile (Flutter)
```bash
cd mobile
flutter pub get
flutter run
```

## 2. Docker Deployment

Launch PostgreSQL and Flask Backend via Docker Compose:
```bash
docker-compose up -d --build
```

## 3. Render.com Deployment (Production)

You can deploy the DairyMitra API and PostgreSQL on [Render](https://render.com) using either **Render Blueprints** (automatic) or the **Render Dashboard UI** (manual).

### Option A: Automatic Blueprint Deployment
1. Push your repository to GitHub.
2. In Render, click **New +** > **Blueprint**.
3. Select your repository. Render will automatically detect [`render.yaml`](file:///d:/Projects/DairyMitra/render.yaml) and configure the web service and PostgreSQL database.
4. Set the required environment variables (`MAIL_USERNAME`, `MAIL_PASSWORD`, etc.) and deploy.

### Option B: Manual Setup via Render Dashboard
1. **Create PostgreSQL Database**:
   - Go to **New +** > **PostgreSQL**.
   - Name: `dairymitra-db`
   - Database: `dairymitra`
   - User: `dairymitra_user`
   - Plan: Free.
   - Click **Create Database** and copy the **Internal Database URL** (e.g. `postgresql://...`).

2. **Create Web Service for Flask Backend**:
   - Go to **New +** > **Web Service**.
   - Connect your GitHub repository.
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT run:app`
   - **Plan**: Free

3. **Configure Environment Variables**:
   Under **Environment Variables**, add:
   - `FLASK_ENV`: `production`
   - `DATABASE_URL`: *(Paste your Render Internal Database URL)*
   - `SECRET_KEY`: *(Generate a random 32+ char key)*
   - `JWT_SECRET_KEY`: *(Generate a random 32+ char key)*
   - `OTP_MOCK_MODE`: `False` (for real emails) or `True` (to view OTP in Render logs)
   - `MAIL_SERVER`: `smtp.gmail.com`
   - `MAIL_PORT`: `587`
   - `MAIL_USE_TLS`: `True`
   - `MAIL_USERNAME`: `your-email@gmail.com`
   - `MAIL_PASSWORD`: `your-google-app-password`
   - `MAIL_DEFAULT_SENDER`: `your-email@gmail.com`

---

## 4. How Email OTP Works on Live Render

### 1. Real Email Delivery (Production)
- Set `OTP_MOCK_MODE=False` and provide a Google 16-character **App Password** (not your regular Gmail password).
- When a user registers or resets password, DairyMitra sends a formatted HTML email with the 6-digit OTP code directly to their inbox.

### 2. Live Render Log Mode (Development / Testing)
- Set `OTP_MOCK_MODE=True`.
- No email credentials required!
- When OTP is requested, DairyMitra writes the 6-digit code directly into the **Render Web Service Logs** tab:
  ```text
  =======================================================
  [DAIRYMITRA EMAIL OTP]
  To: farmer@example.com
  Purpose: REGISTER
  OTP: 839201
  =======================================================
  ```
- Additionally, test code `123456` can be used to verify immediately.

---

## 5. Mobile App Configuration for Live Render

In [`mobile/lib/core/constants/api_endpoints.dart`](file:///d:/Projects/DairyMitra/mobile/lib/core/constants/api_endpoints.dart), update the default base URL with your Render live domain:
```dart
static const String defaultBaseUrl = 'https://dairymitra-api.onrender.com/api/v1';
```
Or set it dynamically at runtime using `SecureStorageService.saveBaseUrl('https://dairymitra-api.onrender.com/api/v1')`.
