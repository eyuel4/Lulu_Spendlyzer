# 📚 Database Schema Documentation — Lulu_Spendlyzer

## Overview

The Lulu_Spendlyzer application uses a relational database (SQLite, via SQLAlchemy ORM) to manage users, their bank cards, transactions, custom categorization, and financial reports. The schema is designed for extensibility, multi-user support, and robust financial data analysis.

---

## Entity-Relationship Diagram (Textual)

- **User** (1) — (1) **UserPreferences**
- **User** (1) — (N) **Card**
- **User** (1) — (N) **Transaction**
- **User** (1) — (N) **CategoryOverride**
- **User** (1) — (N) **Report**
- **User** (1) — (N) **GroceryCategory**
- **User** (1) — (N) **ShoppingCategory**
- **Card** (1) — (N) **Transaction**

---

## Table Descriptions

### 1. User

| Field      | Type      | Description                |
|------------|-----------|----------------------------|
| id         | Integer   | Primary key                |
| name       | String    | User's full name           |
| email      | String    | User's email address       |
| created_at | DateTime  | Account creation timestamp |

---

### 2. UserPreferences

| Field            | Type      | Description                                    |
|------------------|-----------|------------------------------------------------|
| id               | Integer   | Primary key                                    |
| user_id          | Integer   | Foreign key → User.id (unique)                 |
| account_type     | String    | 'personal' or 'family'                         |
| primary_goal     | JSON      | List of financial goals as JSON array          |
| financial_focus  | JSON      | List of focus areas as JSON array              |
| experience_level | String    | 'beginner', 'intermediate', or 'advanced'      |

- **Purpose:** Stores user preferences from the onboarding questionnaire for personalization.

---

### 3. Card

| Field        | Type      | Description                          |
|--------------|-----------|--------------------------------------|
| id           | Integer   | Primary key                          |
| user_id      | Integer   | Foreign key → User.id                |
| bank_name    | String    | Name of the bank                     |
| card_name    | String    | User's label for the card/account    |
| last4        | String    | Last 4 digits of card/account number |
| access_token | String    | Plaid access token                   |
| created_at   | DateTime  | Card link timestamp                  |

---

### 4. Transaction

| Field                | Type      | Description                                 |
|----------------------|-----------|---------------------------------------------|
| id                   | Integer   | Primary key                                 |
| user_id              | Integer   | Foreign key → User.id                       |
| card_id              | Integer   | Foreign key → Card.id                       |
| plaid_transaction_id | String    | Unique Plaid transaction ID (deduplication) |
| name                 | String    | Transaction name                            |
| merchant_name        | String    | Merchant/store name                         |
| date                 | Date      | Transaction date                            |
| amount               | Float     | Transaction amount (+income, -expense)      |
| plaid_category       | String    | Category from Plaid                         |
| custom_category      | String    | User-defined/overridden category            |
| budget_type          | String    | 50/30/20 budget classification              |
| month_id             | String    | e.g., "May_2025"                            |
| created_at           | DateTime  | Ingestion timestamp                         |

---

### 5. CategoryOverride

| Field          | Type      | Description                                  |
|----------------|-----------|----------------------------------------------|
| id             | Integer   | Primary key                                  |
| user_id        | Integer   | Foreign key → User.id                        |
| plaid_category | String    | Plaid's original category                    |
| merchant_name  | String    | (Optional) Merchant for granular override    |
| custom_category| String    | User's custom category                       |

- **Purpose:** Allows users to override Plaid's category, optionally for specific merchants.

---

### 6. Report

| Field         | Type      | Description                                  |
|---------------|-----------|----------------------------------------------|
| id            | Integer   | Primary key                                  |
| user_id       | Integer   | Foreign key → User.id                        |
| month_id      | String    | e.g., "May_2025"                             |
| report_data   | JSON      | Full report data (summary, breakdown, etc.)  |
| total_income  | Float     | Total income for the month                   |
| total_expense | Float     | Total expenses for the month                 |
| net_profit    | Float     | Net profit (income - expenses)               |
| created_at    | DateTime  | Report generation timestamp                  |

- **Purpose:** Stores generated reports for fast retrieval and historical analysis.

---

### 7. GroceryCategory

| Field      | Type      | Description                                  |
|------------|-----------|----------------------------------------------|
| id         | Integer   | Primary key                                  |
| user_id    | Integer   | Foreign key → User.id                        |
| store_name | String    | Store/merchant name for groceries (unique)   |

- **Purpose:** Used for auto-tagging transactions as groceries based on merchant name.

---

### 8. ShoppingCategory

| Field         | Type      | Description                                  |
|---------------|-----------|----------------------------------------------|
| id            | Integer   | Primary key                                  |
| user_id       | Integer   | Foreign key → User.id                        |
| category_name | String    | Shopping category name (unique)              |

- **Purpose:** Used for auto-tagging shopping transactions based on category name.

---

## Design Highlights

- **Multi-user support:** All user data is isolated via `user_id` foreign keys.
- **Extensible categorization:** CategoryOverride, GroceryCategory, and ShoppingCategory enable flexible, user-driven tagging and reporting.
- **Plaid integration:** Card and Transaction tables are designed to securely store Plaid tokens and transaction IDs.
- **Report storage:** Reports are generated and stored as JSON, with summary fields for fast dashboard queries.
- **Auto-tagging:** GroceryCategory and ShoppingCategory enable automated classification of transactions for richer analytics.

---

## Example Use Cases

- When a new transaction is fetched, its `merchant_name` is checked against GroceryCategory and ShoppingCategory for auto-tagging.
- Users can override Plaid's category for a specific merchant or category using CategoryOverride.
- Reports are generated monthly and stored for instant retrieval, including all summary and breakdown data. 