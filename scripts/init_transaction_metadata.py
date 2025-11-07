"""
Database initialization script for transaction metadata.
This script inserts all required metadata for the transaction system:
- Transaction Types (Income, Expense, Transfer, Cash, Check Withdrawn, Wire)
- Expense Categories (Food & Dining, Transportation, etc.)
- Expense Subcategories
- Payment Methods
- Budget Types

Usage:
    python scripts/init_transaction_metadata.py

This script is idempotent and can be run multiple times safely.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

from dotenv import load_dotenv

# Load environment variables
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func

# Import models
from app.models import (
    TransactionType, ExpenseCategory, ExpenseSubcategory,
    PaymentMethod, BudgetType
)
from app.models.base import Base

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL:
    raise RuntimeError("DB_URL environment variable must be set")

# Ensure the database path is absolute
if DATABASE_URL.startswith('sqlite+aiosqlite:///'):
    db_path = DATABASE_URL.replace('sqlite+aiosqlite:///', '')
    if db_path.startswith('./') or db_path.startswith('../'):
        DATABASE_URL = f'sqlite+aiosqlite:///{project_root}/finance.db'

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def check_table_exists(session: AsyncSession, table_name: str) -> bool:
    """Check if a table exists in the database"""
    try:
        await session.execute(select(func.count(1)).select_from(table_name))
        return True
    except Exception:
        return False


async def insert_transaction_types(session: AsyncSession) -> int:
    """Insert transaction types"""
    transaction_types = [
        TransactionType(
            name="Expense",
            description="Spending or expense transactions",
            icon="shopping-bag",
            color="text-red-600",
            is_active=True
        ),
        TransactionType(
            name="Income",
            description="Income or earnings transactions",
            icon="trending-up",
            color="text-green-600",
            is_active=True
        ),
        TransactionType(
            name="Transfer",
            description="Transfers between accounts",
            icon="arrow-right",
            color="text-blue-600",
            is_active=True
        ),
        TransactionType(
            name="Cash",
            description="Cash withdrawal or deposit",
            icon="wallet",
            color="text-yellow-600",
            is_active=True
        ),
        TransactionType(
            name="Check Withdrawn",
            description="Check withdrawal",
            icon="check",
            color="text-purple-600",
            is_active=True
        ),
        TransactionType(
            name="Wire",
            description="Wire transfer",
            icon="send",
            color="text-indigo-600",
            is_active=True
        ),
    ]

    count = 0
    for t_type in transaction_types:
        # Check if already exists
        result = await session.execute(
            select(TransactionType).where(TransactionType.name == t_type.name)
        )
        if not result.scalars().first():
            session.add(t_type)
            count += 1
            print(f"  ✓ Added transaction type: {t_type.name}")
        else:
            print(f"  ⊘ Transaction type already exists: {t_type.name}")

    if count > 0:
        await session.commit()
    return count


async def insert_expense_categories(session: AsyncSession) -> int:
    """Insert expense categories"""
    categories = [
        ExpenseCategory(
            name="Food & Dining",
            description="Groceries, restaurants, food delivery",
            icon="fork-and-knife",
            color="text-orange-600",
            bg_color="bg-orange-100",
            display_order=1,
            is_active=True
        ),
        ExpenseCategory(
            name="Transportation",
            description="Gas, public transit, Uber, car payments",
            icon="car",
            color="text-blue-600",
            bg_color="bg-blue-100",
            display_order=2,
            is_active=True
        ),
        ExpenseCategory(
            name="Shopping",
            description="Clothing, electronics, home goods",
            icon="shopping-bag",
            color="text-purple-600",
            bg_color="bg-purple-100",
            display_order=3,
            is_active=True
        ),
        ExpenseCategory(
            name="Entertainment",
            description="Movies, games, hobbies, subscriptions",
            icon="film",
            color="text-pink-600",
            bg_color="bg-pink-100",
            display_order=4,
            is_active=True
        ),
        ExpenseCategory(
            name="Healthcare",
            description="Medical, dental, pharmacy, health products",
            icon="heart",
            color="text-red-600",
            bg_color="bg-red-100",
            display_order=5,
            is_active=True
        ),
        ExpenseCategory(
            name="Utilities",
            description="Electricity, water, internet, gas bills",
            icon="zap",
            color="text-yellow-600",
            bg_color="bg-yellow-100",
            display_order=6,
            is_active=True
        ),
        ExpenseCategory(
            name="Housing",
            description="Rent, mortgage, property tax, maintenance",
            icon="home",
            color="text-cyan-600",
            bg_color="bg-cyan-100",
            display_order=7,
            is_active=True
        ),
        ExpenseCategory(
            name="Insurance",
            description="Auto, health, home, life insurance",
            icon="shield",
            color="text-green-600",
            bg_color="bg-green-100",
            display_order=8,
            is_active=True
        ),
        ExpenseCategory(
            name="Personal Care",
            description="Haircut, spa, gym, fitness",
            icon="scissors",
            color="text-indigo-600",
            bg_color="bg-indigo-100",
            display_order=9,
            is_active=True
        ),
        ExpenseCategory(
            name="Education",
            description="Tuition, books, courses, training",
            icon="book",
            color="text-teal-600",
            bg_color="bg-teal-100",
            display_order=10,
            is_active=True
        ),
        ExpenseCategory(
            name="Miscellaneous",
            description="Other expenses",
            icon="square",
            color="text-gray-600",
            bg_color="bg-gray-100",
            display_order=11,
            is_active=True
        ),
    ]

    count = 0
    for category in categories:
        result = await session.execute(
            select(ExpenseCategory).where(ExpenseCategory.name == category.name)
        )
        if not result.scalars().first():
            session.add(category)
            count += 1
            print(f"  ✓ Added expense category: {category.name}")
        else:
            print(f"  ⊘ Category already exists: {category.name}")

    if count > 0:
        await session.commit()
    return count


async def insert_expense_subcategories(session: AsyncSession) -> int:
    """Insert expense subcategories"""
    subcategories_data = [
        # Food & Dining
        ("Food & Dining", [
            ("Groceries", "grocery-store"),
            ("Restaurants", "utensils"),
            ("Fast Food", "zap"),
            ("Coffee & Drinks", "coffee"),
            ("Delivery", "truck"),
        ]),
        # Transportation
        ("Transportation", [
            ("Gas", "fuel"),
            ("Public Transit", "train"),
            ("Uber/Lyft", "users"),
            ("Taxi", "navigation"),
            ("Car Payment", "credit-card"),
            ("Car Insurance", "shield"),
            ("Parking", "map-pin"),
        ]),
        # Shopping
        ("Shopping", [
            ("Clothing", "shirt"),
            ("Electronics", "monitor"),
            ("Home & Garden", "home"),
            ("Books", "book"),
            ("Furniture", "inbox"),
        ]),
        # Entertainment
        ("Entertainment", [
            ("Movies", "film"),
            ("Streaming Services", "tv"),
            ("Games", "gamepad2"),
            ("Concerts/Events", "music"),
            ("Hobbies", "palette"),
        ]),
        # Healthcare
        ("Healthcare", [
            ("Doctor Visit", "user-md"),
            ("Medication", "pill"),
            ("Dental", "tooth"),
            ("Gym/Fitness", "activity"),
            ("Mental Health", "smile"),
        ]),
        # Utilities
        ("Utilities", [
            ("Electricity", "zap"),
            ("Water", "droplet"),
            ("Internet", "wifi"),
            ("Gas", "flame"),
            ("Phone", "smartphone"),
        ]),
        # Housing
        ("Housing", [
            ("Rent", "key"),
            ("Mortgage", "home"),
            ("Property Tax", "receipt"),
            ("Maintenance", "wrench"),
            ("Home Improvement", "hammer"),
        ]),
        # Insurance
        ("Insurance", [
            ("Auto Insurance", "shield"),
            ("Health Insurance", "heart"),
            ("Home Insurance", "home"),
            ("Life Insurance", "umbrella"),
        ]),
        # Personal Care
        ("Personal Care", [
            ("Haircut", "scissors"),
            ("Spa", "droplet"),
            ("Gym Membership", "activity"),
            ("Beauty Products", "mirror"),
        ]),
        # Education
        ("Education", [
            ("Tuition", "book"),
            ("Books & Materials", "library"),
            ("Courses", "graduation-cap"),
            ("Training", "zap"),
        ]),
    ]

    count = 0
    for cat_name, subcats in subcategories_data:
        # Get category
        cat_result = await session.execute(
            select(ExpenseCategory).where(ExpenseCategory.name == cat_name)
        )
        category = cat_result.scalars().first()
        if not category:
            print(f"  ⚠ Category not found: {cat_name}")
            continue

        for subcat_name, icon in subcats:
            result = await session.execute(
                select(ExpenseSubcategory).where(
                    (ExpenseSubcategory.name == subcat_name) &
                    (ExpenseSubcategory.expense_category_id == category.id)
                )
            )
            if not result.scalars().first():
                subcat = ExpenseSubcategory(
                    name=subcat_name,
                    expense_category_id=category.id,
                    icon=icon,
                    is_active=True,
                    display_order=0
                )
                session.add(subcat)
                count += 1
                print(f"  ✓ Added subcategory: {cat_name} → {subcat_name}")
            else:
                print(f"  ⊘ Subcategory already exists: {cat_name} → {subcat_name}")

    if count > 0:
        await session.commit()
    return count


async def insert_payment_methods(session: AsyncSession) -> int:
    """Insert payment methods"""
    payment_methods = [
        PaymentMethod(
            name="Credit Card",
            description="Credit card payment",
            icon="credit-card",
            color="text-blue-600",
            display_order=1,
            is_active=True
        ),
        PaymentMethod(
            name="Debit Card",
            description="Debit card payment",
            icon="credit-card",
            color="text-green-600",
            display_order=2,
            is_active=True
        ),
        PaymentMethod(
            name="Cash",
            description="Cash payment",
            icon="wallet",
            color="text-yellow-600",
            display_order=3,
            is_active=True
        ),
        PaymentMethod(
            name="Check",
            description="Check payment",
            icon="check",
            color="text-purple-600",
            display_order=4,
            is_active=True
        ),
        PaymentMethod(
            name="Bank Transfer",
            description="ACH/Bank transfer",
            icon="arrow-right",
            color="text-indigo-600",
            display_order=5,
            is_active=True
        ),
        PaymentMethod(
            name="Wire Transfer",
            description="Wire transfer",
            icon="send",
            color="text-red-600",
            display_order=6,
            is_active=True
        ),
        PaymentMethod(
            name="Mobile Payment",
            description="Mobile payment (Venmo, PayPal, etc.)",
            icon="smartphone",
            color="text-cyan-600",
            display_order=7,
            is_active=True
        ),
    ]

    count = 0
    for method in payment_methods:
        result = await session.execute(
            select(PaymentMethod).where(PaymentMethod.name == method.name)
        )
        if not result.scalars().first():
            session.add(method)
            count += 1
            print(f"  ✓ Added payment method: {method.name}")
        else:
            print(f"  ⊘ Payment method already exists: {method.name}")

    if count > 0:
        await session.commit()
    return count


async def insert_budget_types(session: AsyncSession) -> int:
    """Insert budget types"""
    budget_types = [
        BudgetType(
            name="Essential",
            description="Necessary expenses (food, rent, utilities)",
            icon="alert-circle",
            color="text-red-600",
            display_order=1,
            is_active=True
        ),
        BudgetType(
            name="Discretionary",
            description="Optional spending (entertainment, shopping)",
            icon="smile",
            color="text-green-600",
            display_order=2,
            is_active=True
        ),
        BudgetType(
            name="Investment",
            description="Money saved or invested for future",
            icon="trending-up",
            color="text-blue-600",
            display_order=3,
            is_active=True
        ),
        BudgetType(
            name="Emergency",
            description="Unexpected or emergency expenses",
            icon="alert-triangle",
            color="text-orange-600",
            display_order=4,
            is_active=True
        ),
    ]

    count = 0
    for btype in budget_types:
        result = await session.execute(
            select(BudgetType).where(BudgetType.name == btype.name)
        )
        if not result.scalars().first():
            session.add(btype)
            count += 1
            print(f"  ✓ Added budget type: {btype.name}")
        else:
            print(f"  ⊘ Budget type already exists: {btype.name}")

    if count > 0:
        await session.commit()
    return count


async def main():
    """Main function to initialize all metadata"""
    print("\n" + "="*70)
    print("Transaction Metadata Initialization Script")
    print("="*70 + "\n")

    async with engine.begin() as conn:
        # Create all tables first
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created/verified\n")

    async with AsyncSessionLocal() as session:
        print("Initializing metadata...\n")

        print("1. Inserting Transaction Types...")
        count1 = await insert_transaction_types(session)
        print(f"   Result: {count1} new types added\n")

        print("2. Inserting Expense Categories...")
        count2 = await insert_expense_categories(session)
        print(f"   Result: {count2} new categories added\n")

        print("3. Inserting Expense Subcategories...")
        count3 = await insert_expense_subcategories(session)
        print(f"   Result: {count3} new subcategories added\n")

        print("4. Inserting Payment Methods...")
        count4 = await insert_payment_methods(session)
        print(f"   Result: {count4} new payment methods added\n")

        print("5. Inserting Budget Types...")
        count5 = await insert_budget_types(session)
        print(f"   Result: {count5} new budget types added\n")

        total = count1 + count2 + count3 + count4 + count5
        print("="*70)
        print(f"✓ Initialization complete! Total new records: {total}")
        print("="*70 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
