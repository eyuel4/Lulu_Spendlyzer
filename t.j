1. Objective

Build an intuitive personal finance dashboard that allows users to clearly visualize their monthly expense and income breakdown, compare trends over time, and update data seamlessly through Plaid API sync or bank statement upload.

2. Key Features
A. Date Range Selector

Dropdown on top right/left with options:

Month/Year Selector (e.g., August 2025)

Predefined Ranges: Last 3 Months, Last 6 Months, YTD, Full Year

On selection, all dashboard components refresh with the chosen range.

B. Summary Section (Top Row Cards)

Cards showing:

Total Income

Total Expenses

Net Savings (Income – Expense)

Optional: % Change vs Previous Period

Cards should use color cues:

Green = Positive trend

Red = Negative trend

C. Charts & Visualizations

Pie/Donut Chart – Expense breakdown by category (e.g., Food, Rent, Travel).

Bar/Line Chart – Income vs Expense trend over time (per month).

Optional: Stacked bar chart for category-wise expenses per month.

D. Transaction Feed (Bottom Section)

Paginated, searchable list of transactions.

Columns: Date, Merchant, Category, Amount, Source (Plaid/Upload).

Highlight newly imported transactions.

E. Data Import Options

If Plaid API connected: Show "Fetch Latest Transactions" button (CTA).

If Statement Upload: Show message → “Don’t worry! Already imported transactions will be automatically detected and skipped.”

Both flows should refresh dashboard seamlessly.

3. UX Guidelines

One-screen dashboard for clarity: summary + charts + transaction list.

Use the UI rule I have spacified. Implement a dark theme and light theme alternative.

Responsive design → must look clean and Responsive in mobile first, desktop, tablet, mobile.

