# DairyMitra REST API Specification

All API endpoints follow RESTful standards and return standardized JSON envelopes.

## Base URL
`/api/v1`

## Common Response Structure

### Success Response (HTTP 200 / 201)
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Error Response (HTTP 400 / 401 / 403 / 404 / 422 / 500)
```json
{
  "success": false,
  "message": "Descriptive error message",
  "errors": { ... }
}
```

---

## 1. Authentication Endpoints (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/send-otp` | Generate and dispatch 6-digit OTP to user's email | No |
| `POST` | `/auth/verify-otp` | Verify email OTP code | No |
| `POST` | `/auth/register` | Register new farmer account (requires verified OTP) | No |
| `POST` | `/auth/login` | Email/password login. Returns access & refresh tokens | No |
| `POST` | `/auth/refresh` | Refresh expired access token with refresh token | Refresh Token |
| `POST` | `/auth/forgot-password` | Request password reset OTP | No |
| `POST` | `/auth/reset-password` | Reset password using valid reset OTP | No |
| `GET` | `/auth/me` | Fetch authenticated user profile & accessible farms | Bearer JWT |

---

## 2. Farm Management Endpoints (`/api/v1/farms`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/farms` | List user's farms | Bearer JWT |
| `POST` | `/farms` | Create new farm | Bearer JWT |
| `GET` | `/farms/{id}` | Get farm details | Bearer JWT |
| `PUT` | `/farms/{id}` | Update farm profile | Bearer JWT |
| `GET` | `/farms/{id}/dashboard` | Comprehensive dashboard summary (milk, revenue, profit, alerts) | Bearer JWT |

---

## 3. Animal Management Endpoints (`/api/v1/animals`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/animals?farm_id={id}` | List all animals with optional filter | Bearer JWT |
| `POST` | `/animals` | Register a new animal (cow/buffalo) | Bearer JWT |
| `GET` | `/animals/{id}` | Animal detail + milk stats & averages | Bearer JWT |
| `PUT` | `/animals/{id}` | Update animal details | Bearer JWT |
| `DELETE` | `/animals/{id}` | Soft-delete / deactivate animal | Bearer JWT |
| `GET` | `/animals/{id}/health` | List animal health / vaccination records | Bearer JWT |
| `POST` | `/animals/{id}/health` | Add health / vaccination record | Bearer JWT |

---

## 4. Milk Production Endpoints (`/api/v1/milk`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/milk?farm_id={id}&date={date}` | List daily animal-wise milk records | Bearer JWT |
| `POST` | `/milk` | Record morning/evening milk production | Bearer JWT |
| `PUT` | `/milk/{id}` | Update milk record (creates audit trail) | Bearer JWT |
| `GET` | `/milk/summary?farm_id={id}&period={daily/weekly/monthly}` | Milk yield metrics | Bearer JWT |
| `GET` | `/milk/price?farm_id={id}` | Get current milk price history | Bearer JWT |
| `POST` | `/milk/price` | Set new effective milk price | Bearer JWT |

---

## 5. Customer & Delivery Endpoints (`/api/v1/customers`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/customers?farm_id={id}` | List customers with balances | Bearer JWT |
| `POST` | `/customers` | Register customer | Bearer JWT |
| `GET` | `/customers/{id}` | Customer detail & delivery history | Bearer JWT |
| `PUT` | `/customers/{id}` | Update customer | Bearer JWT |
| `GET` | `/customers/deliveries?farm_id={id}&date={date}` | Daily delivery register | Bearer JWT |
| `POST` | `/customers/deliveries` | Record daily delivery / skip | Bearer JWT |

---

## 6. Billing & Payments (`/api/v1/bills`, `/api/v1/payments`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/bills/generate` | Generate customer bill for date range | Bearer JWT |
| `GET` | `/bills/{id}` | View bill breakdown & payment status | Bearer JWT |
| `GET` | `/bills/{id}/pdf` | Generate printable PDF bill | Bearer JWT |
| `POST` | `/payments/create-order` | Create server-side Razorpay order | Bearer JWT |
| `POST` | `/payments/verify` | Verify Razorpay HMAC signature & update customer balance | Bearer JWT |
| `POST` | `/payments/cash` | Record direct cash/offline payment | Bearer JWT |

---

## 7. Expenses, Ghee, Inventory & Reports

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/expenses?farm_id={id}` | List expenses with category filters | Bearer JWT |
| `POST` | `/expenses` | Record expense | Bearer JWT |
| `GET` | `/ghee?farm_id={id}` | Ghee batches and stock | Bearer JWT |
| `POST` | `/ghee/produce` | Record ghee production from milk | Bearer JWT |
| `GET` | `/inventory?farm_id={id}` | List inventory items & stock levels | Bearer JWT |
| `POST` | `/inventory/transaction` | Log purchase, usage, adjustment | Bearer JWT |
| `GET` | `/reports/profit?farm_id={id}` | Centralized Financial Report | Bearer JWT |
| `POST` | `/ai/ask` | Natural language business assistant | Bearer JWT |
| `GET` | `/ai/insights?farm_id={id}` | AI forecast & trend insights | Bearer JWT |
| `POST` | `/sync` | Bulk offline sync queue processing | Bearer JWT |
