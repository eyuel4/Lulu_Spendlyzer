# 📝 Product Requirements Document (PRD)

**Project Name:** Personal Finance Automation System  
**Author:** Eyuel Taddese  
**Date:** June 18, 2025  
**Version:** 1.0  

---

## 📌 Project Overview

This application is a personal finance dashboard that connects to multiple banks using the **Plaid API**. It fetches all user-linked transactions, categorizes them using both **Plaid's auto-categorization** and **user-defined categories**, stores the data in a **SQLite database**, and displays monthly reports in a modern **Angular UI**.

The application runs **locally only** and supports **multiple users**, **multiple banks and cards per user**, and **manual report generation per month**. It is optimized for extensibility and future enhancements (e.g., budget alerts, family roles, email reports).

---

## ⚙️ Technology Stack

| Layer       | Stack                      |
|-------------|----------------------------|
| Frontend    | Angular 17+                |
| Backend     | Python 3.10+ with FastAPI  |
| API Client  | Plaid Python SDK           |
| Database    | SQLite with SQLAlchemy ORM |
| Charts      | Angular + chart.js         |
| Deployment  | Localhost only             |

---

## 🗃️ Database Schema (SQLAlchemy ORM)

### `User`

```python
id: int (PK)
name: str
email: str
created_at: datetime
Card
python
Copy
Edit
id: int (PK)
user_id: int (FK → User.id)
bank_name: str
card_name: str
last4: str
access_token: str
created_at: datetime
Transaction
python
Copy
Edit
id: int (PK)
user_id: int (FK → User.id)
card_id: int (FK → Card.id)
name: str               # transaction name
merchant_name: str      # from Plaid
date: date
amount: float
plaid_category: str     # original from Plaid
custom_category: str    # optionally overridden by user
budget_type: str        # 50, 30, or 20
month_id: str           # format: "May_2025"
created_at: datetime
🧩 Features
1. Plaid Integration (Backend)
Endpoint to generate a Plaid Link Token per user

Endpoint to exchange public_token for access_token

Store access_token in Card table

Scheduled or manual endpoint to fetch transactions from Plaid for a given month and insert into Transaction table

Filter out duplicates using transaction IDs (optional for later)

2. Manual Report Generation
POST /generate-report?month=May_2025&user_id=1

For each card under user, fetch transactions from Plaid within given month range

Apply Plaid category + user category (if override rules exist — phase 2)

Calculate:

Monthly total income

Monthly total expenses

Net profit = income - expenses

Total per custom category

Total per card

3. Angular Frontend UI
Home Page
Show list of months (e.g., current year months)

For each month:

✅ “View Report” if data exists

❌ “Generate Report” button if data missing

Button triggers POST /generate-report

Report Page (/report/:month)
Show:

Header summary:

Total income

Total expense

Net profit

Pie chart by custom category

Table grouped by category:

Transactions nested under each category

Columns: Date, Merchant, Amount, Card, Budget Type

Filter/sortable by category, card, amount, etc.

🛠 API Endpoints
Method	URL	Description
GET	/link/token/create?user_id=1	Create Plaid Link token
POST	/link/exchange	Exchange public token for access token
POST	/generate-report	Body: { "month": "May_2025", "user_id": 1 }
GET	/reports?user_id=1	Get list of months and report status
GET	/report/{month}?user_id=1	Get full report data for month
GET	/transactions?user_id=1&month=May_2025	Raw transactions (optional)

📊 Report Calculations
Total income = sum of positive values in amount

Total expenses = sum of negative values in amount

Net profit = income - expenses

Totals per custom category (e.g., Grocery, Rent)

Totals per card (aggregated by card_name)

Budget type summary (50, 30, 20)

🧠 Categorization Strategy
Store Plaid category (plaid_category) for reference

Use override mapping table or rule engine (future phase) to tag custom_category

Allow frontend to suggest overrides (not implemented now)

🧪 Development & Testing Notes
Use Plaid sandbox (ins_109508) for test institutions

Test with fake credentials: user_good / pass_good

SQLite DB stored as finance.db

Seed scripts available to pre-populate users/cards

All environment configs in .env

🌱 Environment Variables (.env)
env
Copy
Edit
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ENV=sandbox

EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_TO=your_email@gmail.com

DB_URL=sqlite:///finance.db
🚧 Future Enhancements
Budget limits per category

Overspending alerts (monthly)

Excel export or PDF reports

Email integration for report delivery

Multi-family user roles (spouse, kids, etc.)

Auth system for login and token security

🧾 Sample Transactions Schema (JSON)
json
Copy
Edit
{
  "month": "May_2025",
  "user_id": 1,
  "total_income": 12000,
  "total_expense": 8200,
  "net_profit": 3800,
  "categories": [
    {
      "category": "Grocery",
      "total": 1800,
      "transactions": [
        {
          "date": "2025-05-03",
          "merchant_name": "Costco",
          "amount": -300.50,
          "bank": "Chase",
          "card": "Chase 4016",
          "budget_type": "50"
        }
      ]
    }
  ],
  "cards_summary": [
    {
      "card": "Chase 4016",
      "total_spent": 4200
    }
  ]
}
✅ Summary
This app will allow users to link their bank accounts via Plaid, fetch monthly transactions, categorize and track expenses, and view them in a rich UI by month and category — all from a locally hosted Angular + Python app, designed for future extension to support multi-user families and budget alerts.