# DairyMitra — Smart Dairy & Farm Business Management System

> **A modern, production-grade, offline-first dairy and farm management platform built for farmers to replace paper notebooks with digital precision, automated billing, payment verification, and AI insights.**

---

## 1. Project Overview

DairyMitra empowers dairy farmers managing cows, buffaloes, daily milk yields, customer milk distribution, ghee production, feed & medical expenses, customer ledger balances, and profitability.

Key Highlights:
- **Zero Paper Loss**: Instant single-tap morning & evening milk registers.
- **Offline-First Resilience**: Full SQLite offline capability with idempotent cloud sync queue.
- **Centralized Financial Truth**: Backend engine guarantees that `Revenue - Expenses = Net Profit` and prevents client-side tampering.
- **Razorpay Integration**: Server-side HMAC-SHA256 signature verification for customer bill payments.
- **AI Analytics & Assistant**: Natural language farmer assistant, profit forecasting, and statistical milk anomaly detection.
- **Email OTP Authentication**: 6-digit cryptographic OTPs with SHA-256 hashing, expiration, and rate limiting.

---

## 2. Technology Stack

### Mobile (Flutter)
- **Framework**: Flutter 3.44+ / Dart 3.12+
- **State Management**: Riverpod (`flutter_riverpod`)
- **Networking**: Dio with JWT Bearer interceptor & automatic refresh token rotation
- **Routing**: GoRouter with ShellRoute navigation
- **Offline Storage**: SQLite (`sqflite` + `sqflite_common_ffi`)
- **Credentials**: `flutter_secure_storage`
- **Charts & UI**: `fl_chart`, `google_fonts`, Material 3

### Backend (Python Flask)
- **Framework**: Flask 3.1+ (Application Factory pattern)
- **Database & ORM**: PostgreSQL / SQLite fallback via Flask-SQLAlchemy & Flask-Migrate
- **Auth & Security**: Flask-JWT-Extended, werkzeug password hashing, SHA-256 OTP hashing
- **Rate Limiting & CORS**: Flask-Limiter, Flask-Cors
- **Invoicing**: ReportLab PDF generation
- **Payments**: Razorpay official SDK

---

## 3. Project Structure

```text
dairymitra/
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Flask App Factory & Error Handlers
│   │   ├── config.py             # Dev, Test, Prod configuration
│   │   ├── extensions.py         # SQLAlchemy, JWT, Limiter, CORS singletons
│   │   ├── models/               # SQLAlchemy Models (User, Farm, Animal, Milk, Customer, Bill, Payment, Expense, Ghee, Inventory, Sync)
│   │   ├── api/                  # Blueprint REST routes (/auth, /farms, /animals, /milk, /customers, /bills, /payments, /expenses, /ghee, /inventory, /reports, /ai, /sync)
│   │   ├── services/             # AuthService, FinancialEngine, EmailService, AuditService
│   │   └── utils/                # Standard JSON envelopes & RBAC decorators
│   ├── run.py                    # Flask development server runner
│   ├── requirements.txt          # Python dependencies
│   └── Dockerfile
│
├── mobile/                       # Flutter Mobile Application
│   ├── lib/
│   │   ├── core/                 # Constants, Colors, Theme, ApiClient, SecureStorage, LocalDB
│   │   ├── features/
│   │   │   ├── auth/             # Login, Register, Email OTP, Password Reset
│   │   │   ├── dashboard/        # Live yields, financials, 7-day trend charts
│   │   │   ├── milk/             # Daily morning & evening entry
│   │   │   ├── customers/        # Customer directory, delivery register, bill & Razorpay UI
│   │   │   ├── expenses/         # Categorized farm expenses
│   │   │   ├── animals/          # Herd profile, 7-day & 30-day averages, vaccinations
│   │   │   ├── ghee_inventory/   # Ghee batches, stock & feed tracking
│   │   │   ├── ai_assistant/     # Conversational business assistant
│   │   │   ├── reports/          # P&L statements, CSV exports
│   │   │   └── navigation/       # MainNavScaffold & offline sync badge
│   │   ├── routes/               # GoRouter configuration
│   │   └── main.dart             # App Entrypoint
│   └── pubspec.yaml
│
├── database/
│   └── seed/
│       └── seed_data.py          # Realistic demo dataset (10 animals, 20 customers, 14 days milk)
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── api.md
│   └── deployment.md
├── tests/
│   └── test_backend.py           # Unit & API integration tests
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 4. Getting Started

### 1. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default development settings run with mock email mode and local SQLite fallback, requiring zero external setup to test immediately.

### 2. Backend Setup & Seeding
```bash
# In backend directory:
python -m venv venv
venv\Scripts\activate          # On Windows
# or: source venv/bin/activate # On Linux/macOS

pip install -r requirements.txt

# Run seed data to populate demo farmer and herd:
python ../database/seed/seed_data.py

# Start Flask server:
python run.py
```
*API will run at `http://127.0.0.1:5001` (Status Dashboard: `http://127.0.0.1:5001/`, API: `http://127.0.0.1:5001/api/v1`).*

**Demo Farmer Credentials:**
- Email: `farmer@dairymitra.com`
- Password: `DairyMitra@2026`

### 3. Flutter Mobile App Setup
```bash
cd mobile
flutter pub get
flutter run
```

---

## 5. Automated Tests

Run backend tests verifying OTP hashing, authentication, and the financial engine:
```bash
backend\venv\Scripts\pytest tests
```

---

## 6. Offline-First Architecture

1. When internet is disconnected, milk entries and deliveries are written to the local SQLite database (`offline_milk`, `offline_deliveries`).
2. Each offline item is queued into `sync_queue` with a client UUID (`client_sync_id`).
3. When network connectivity is restored, the `Sync Now` badge in the mobile header sends the batch payload to `POST /api/v1/sync`.
4. The Flask backend applies the batch with strict idempotency, ensuring duplicate records are never created.

---

## 7. Security & Payments

- Sensitive keys (`RAZORPAY_KEY_SECRET`, `JWT_SECRET_KEY`) strictly exist in the backend environment.
- Card credentials, UPI PINs, and bank passwords are never received or stored.
- Payments are only confirmed after the backend validates the Razorpay cryptographic HMAC-SHA256 signature.
