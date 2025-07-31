# 📝 Product Requirements Document (PRD)

**Project Name:** Lulu_Spendlyzer  
**Author:** Eyuel Taddese  
**Date:** June 18, 2025  
**Version:** 1.1  

---

## 📌 Project Overview

**Spendlyzer** is a personal finance dashboard and automation app that:
- Connects to multiple banks using **Plaid**
- Pulls transactions per card and per month
- Categorizes spending using both **Plaid categories** and **custom categories**
- Generates monthly reports with insights
- Supports **individual** and **family/group** accounts
- Runs fully on **localhost** using Angular + FastAPI + SQLite (or MySQL)

---

## ⚙️ Technology Stack

| Layer       | Stack                      |
|-------------|----------------------------|
| Frontend    | Angular 17+                |
| Backend     | Python 3.10+ with FastAPI  |
| API Client  | Plaid Python SDK           |
| Database    | SQLite (or optional MySQL) |
| ORM         | SQLAlchemy (async)         |
| Email (optional)| SMTP (for invite flows)|
| Deployment  | Localhost only             |

---

## 👥 User Account Modes

### 1. Individual Account
- Single user, links multiple banks/cards
- Sees only their own transactions and reports

### 2. Family/Group Account
- Primary account owner
- Can invite additional members (spouse, partner, children)
- All users share a **FamilyGroup**
- Each user may link their own bank accounts
- Shared view of total household spending

---

## 🗃️ Data Model (SQLAlchemy ORM)

### `User`

```python
id: int (PK)
first_name: str
last_name: str
email: str
password_hash: str
is_primary: bool  # True if the main account holder
family_group_id: int (nullable FK → FamilyGroup.id)
created_at: datetime
