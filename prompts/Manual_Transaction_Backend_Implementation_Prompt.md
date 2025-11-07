# Manual Transaction Backend Implementation Prompt

**Project:** Lulu_Spendlyzer - Personal Finance Dashboard  
**Feature:** Manual Transaction Management Backend System  
**Estimated Time:** 1+ hours, 8+ turns  
**Priority:** High - Core feature implementation  

---

## 🎯 **Implementation Overview**

Implement a comprehensive backend system for manual transaction management that supports individual and family accounts, with full CRUD operations, data validation, caching, and audit logging. This system will power the existing frontend manual transaction modal.

---

## 📋 **Detailed Requirements**

### **Phase 1: Database Schema & Models (Turns 1-2)**

**Task 1.1: Create Missing Database Models**
- Create `Category` model with fields: id, name, icon, color, bg_color, user_id (nullable), family_group_id (nullable), created_at
- Create `BankType` model with fields: id, name, icon, user_id, created_at  
- Create `Card` model with fields: id, name, bank_type_id, last_four_digits, user_id, is_active, created_at
- Create `BudgetType` model with fields: id, name, description, user_id, family_group_id (nullable), created_at
- Create `Subcategory` model with fields: id, name, category_id, user_id, family_group_id (nullable), created_at
- Update existing `Transaction` model to support manual transactions with new fields:
  - category_id (FK to Category)
  - subcategory_id (nullable FK to Subcategory) 
  - budget_type_id (nullable FK to BudgetType)
  - bank_type_id (nullable FK to BankType)
  - card_id (nullable FK to Card)
  - is_manual (boolean, default True)
  - merchant (string, nullable)
  - description (string, nullable)

**Task 1.2: Database Schema Updates**
- Update `/app/core/init_db.py` to include all new models
- Add proper foreign key relationships and indexes
- Ensure backward compatibility with existing data
- Add database migration logic for new fields

**Success Criteria:**
- All models created with proper relationships
- Database schema updated without breaking existing data
- Foreign key constraints properly defined
- Indexes added for performance optimization

---

### **Phase 2: API Schemas & Validation (Turn 3)**

**Task 2.1: Create Pydantic Schemas**
- `CategoryCreate`, `CategoryUpdate`, `CategoryResponse` schemas
- `BankTypeCreate`, `BankTypeUpdate`, `BankTypeResponse` schemas  
- `CardCreate`, `CardUpdate`, `CardResponse` schemas
- `BudgetTypeCreate`, `BudgetTypeUpdate`, `BudgetTypeResponse` schemas
- `SubcategoryCreate`, `SubcategoryUpdate`, `SubcategoryResponse` schemas
- Update `TransactionCreate`, `TransactionUpdate`, `TransactionResponse` schemas
- Add validation rules for all fields (required fields, data types, constraints)

**Task 2.2: Request/Response Models**
- Create comprehensive request/response models for all CRUD operations
- Add pagination support for list endpoints
- Include filtering and sorting options
- Add bulk operation schemas for batch imports

**Success Criteria:**
- All schemas properly defined with validation
- Request/response models support all required operations
- Validation rules prevent invalid data entry
- Pagination and filtering properly implemented

---

### **Phase 3: Service Layer Implementation (Turns 4-5)**

**Task 3.1: Category Management Service**
- Implement `CategoryService` with methods:
  - `create_category()` - Create new category
  - `get_categories()` - List user/family categories with filtering
  - `update_category()` - Update category details
  - `delete_category()` - Soft delete category
  - `get_category_by_id()` - Get specific category
  - `get_system_categories()` - Get default system categories
  - `get_family_categories()` - Get family group categories

**Task 3.2: Bank & Card Management Service**
- Implement `BankTypeService` with CRUD operations
- Implement `CardService` with methods:
  - `create_card()` - Add new card
  - `get_user_cards()` - List user's cards
  - `update_card()` - Update card details
  - `deactivate_card()` - Soft delete card
  - `get_card_by_id()` - Get specific card

**Task 3.3: Budget & Subcategory Services**
- Implement `BudgetTypeService` with full CRUD operations
- Implement `SubcategoryService` with methods:
  - `get_subcategories_by_category()` - Get subcategories for a category
  - `create_subcategory()` - Create new subcategory
  - `update_subcategory()` - Update subcategory
  - `delete_subcategory()` - Delete subcategory

**Task 3.4: Enhanced Transaction Service**
- Extend existing `TransactionService` with manual transaction support:
  - `create_manual_transaction()` - Create manual transaction
  - `update_manual_transaction()` - Update manual transaction
  - `get_manual_transactions()` - List manual transactions with filtering
  - `bulk_create_transactions()` - Bulk import transactions
  - `get_transaction_summary()` - Enhanced summary with manual transactions
  - `validate_transaction_data()` - Data validation
  - `categorize_transaction()` - Auto-categorization logic

**Success Criteria:**
- All services implement proper error handling
- Database operations are optimized with proper queries
- Caching implemented for frequently accessed data
- Audit logging for all operations
- Family group support for shared data

---

### **Phase 4: API Endpoints Implementation (Turns 6-7)**

**Task 4.1: Category Management Endpoints**
- `POST /categories/` - Create category
- `GET /categories/` - List categories with filtering
- `GET /categories/{id}` - Get specific category
- `PUT /categories/{id}` - Update category
- `DELETE /categories/{id}` - Delete category
- `GET /categories/system/` - Get system default categories
- `POST /categories/bulk/` - Bulk create categories

**Task 4.2: Bank & Card Management Endpoints**
- `POST /bank-types/` - Create bank type
- `GET /bank-types/` - List bank types
- `POST /cards/` - Create card
- `GET /cards/` - List user cards
- `PUT /cards/{id}` - Update card
- `DELETE /cards/{id}` - Deactivate card

**Task 4.3: Budget & Subcategory Endpoints**
- `POST /budget-types/` - Create budget type
- `GET /budget-types/` - List budget types
- `POST /subcategories/` - Create subcategory
- `GET /subcategories/` - List subcategories with category filtering
- `PUT /subcategories/{id}` - Update subcategory
- `DELETE /subcategories/{id}` - Delete subcategory

**Task 4.4: Enhanced Transaction Endpoints**
- `POST /transactions/manual/` - Create manual transaction
- `PUT /transactions/{id}` - Update transaction (manual or imported)
- `GET /transactions/manual/` - List manual transactions
- `POST /transactions/bulk/` - Bulk import transactions
- `GET /transactions/summary/` - Enhanced summary endpoint
- `POST /transactions/categorize/` - Auto-categorize transaction

**Success Criteria:**
- All endpoints properly authenticated and authorized
- Input validation and error handling implemented
- Proper HTTP status codes and error messages
- Rate limiting and security measures
- Comprehensive API documentation

---

### **Phase 5: Data Integration & Frontend Connection (Turn 8)**

**Task 5.1: Frontend Integration**
- Update frontend services to call new backend endpoints
- Replace mock data in manual transaction modal with real API calls
- Implement proper error handling and loading states
- Add data validation on frontend

**Task 5.2: Data Migration & Seeding**
- Create default system categories (Food & Dining, Transportation, Shopping, etc.)
- Create default budget types (Essential, Discretionary, Investment, Emergency)
- Create default bank types (Chase, Bank of America, Wells Fargo, etc.)
- Migrate existing transaction data if needed

**Task 5.3: Testing & Validation**
- Test all CRUD operations
- Validate data integrity and relationships
- Test family group functionality
- Performance testing with large datasets
- Security testing for authorization

**Success Criteria:**
- Frontend successfully connects to backend
- All CRUD operations working correctly
- Data validation preventing invalid entries
- Family group functionality working
- Performance acceptable for large datasets

---

## 🔧 **Technical Requirements**

### **Database Requirements:**
- Use SQLAlchemy async operations
- Implement proper foreign key relationships
- Add database indexes for performance
- Support both SQLite and MySQL
- Maintain backward compatibility

### **API Requirements:**
- FastAPI with async/await patterns
- JWT authentication for all endpoints
- Proper error handling and HTTP status codes
- Input validation using Pydantic
- Rate limiting and security measures

### **Caching Requirements:**
- Redis caching for frequently accessed data
- Cache invalidation on data updates
- Performance optimization for large datasets
- Family group data caching

### **Security Requirements:**
- User-specific data access control
- Family group authorization
- Audit logging for all operations
- Input sanitization and validation
- SQL injection prevention

### **Performance Requirements:**
- Optimized database queries
- Efficient pagination
- Bulk operation support
- Caching for frequently accessed data
- Response time < 200ms for most operations

---

## 📁 **File Structure to Create/Modify**

### **New Files to Create:**
```
app/models/category.py
app/models/bank_type.py  
app/models/budget_type.py
app/models/subcategory.py
app/schemas/category.py
app/schemas/bank_type.py
app/schemas/budget_type.py
app/schemas/subcategory.py
app/routes/category.py
app/routes/bank_type.py
app/routes/budget_type.py
app/routes/subcategory.py
app/services/category_service.py
app/services/bank_type_service.py
app/services/budget_type_service.py
app/services/subcategory_service.py
```

### **Files to Modify:**
```
app/models/transaction.py (update)
app/models/__init__.py (add new models)
app/schemas/transaction.py (update)
app/routes/transaction.py (enhance)
app/services/transaction_service.py (enhance)
app/core/init_db.py (add new models)
app/main.py (register new routes)
```

---

## 🎯 **Success Metrics**

### **Functional Requirements:**
- ✅ All CRUD operations working for categories, bank types, cards, budget types, subcategories
- ✅ Manual transaction creation, editing, and deletion
- ✅ Family group support for shared data
- ✅ Bulk import/export functionality
- ✅ Data validation and error handling
- ✅ Frontend integration with real backend

### **Performance Requirements:**
- ✅ API response times < 200ms for single operations
- ✅ Bulk operations handle 100+ transactions efficiently
- ✅ Database queries optimized with proper indexing
- ✅ Caching reduces database load by 50%+

### **Security Requirements:**
- ✅ User-specific data access control
- ✅ Family group authorization working
- ✅ All operations properly audited
- ✅ Input validation preventing malicious data

---

## 🚀 **Implementation Notes**

1. **Start with database models** - Foundation for everything else
2. **Implement services before endpoints** - Business logic first
3. **Test each phase thoroughly** - Don't move to next phase until current is complete
4. **Use existing patterns** - Follow established code structure
5. **Implement caching early** - Performance is critical
6. **Add comprehensive logging** - Debugging and audit trails
7. **Test family group functionality** - Key differentiator
8. **Validate all data flows** - End-to-end testing required

---

## ⚠️ **Critical Dependencies**

- Existing authentication system must work
- Database connection and Redis caching must be functional
- Frontend manual transaction modal must be ready for integration
- Family group system must be operational
- Audit logging system must be working

---

**This implementation will take 8+ turns and 1+ hours to complete properly. Each phase builds on the previous one, so don't skip ahead. Focus on quality over speed - this is a core feature that users will interact with daily.**

