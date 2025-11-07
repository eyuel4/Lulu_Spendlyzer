import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ManualTransactionService, ManualTransaction, BulkUploadResponse } from './manual-transaction.service';
import { CacheService } from './cache.service';

describe('ManualTransactionService', () => {
  let service: ManualTransactionService;
  let httpMock: HttpTestingController;
  let cacheService: CacheService;

  const mockTransaction: ManualTransaction = {
    id: 1,
    user_id: 123,
    date: '2025-10-15',
    amount: 45.99,
    currency: 'USD',
    description: 'Groceries',
    merchant: 'Whole Foods',
    notes: 'Weekly grocery run',
    transaction_type_id: 1,
    expense_category_id: 1,
    expense_subcategory_id: 1,
    payment_method_id: 1,
    budget_type_id: 1,
    card_id: 1,
    is_shared: false,
    is_manual: true,
    month_id: '2025-10'
  };

  const mockMetadata = {
    transaction_types: [
      { id: 1, name: 'Expense', description: 'Expense transaction', icon: 'shopping-bag', color: 'text-red-600' }
    ],
    expense_categories: [
      { id: 1, name: 'Food & Dining', description: 'Food expenses', icon: 'fork', color: 'text-orange-600', bg_color: 'bg-orange-100' }
    ],
    payment_methods: [
      { id: 1, name: 'Credit Card', description: 'Credit card payment', icon: 'credit-card', color: 'text-blue-600' }
    ],
    budget_types: [
      { id: 1, name: 'Essential', description: 'Essential expense', icon: 'alert-circle', color: 'text-red-600' }
    ]
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ManualTransactionService, CacheService]
    });

    service = TestBed.inject(ManualTransactionService);
    httpMock = TestBed.inject(HttpTestingController);
    cacheService = TestBed.inject(CacheService);

    // Mock localStorage
    let store: { [key: string]: string } = {};
    const mockLocalStorage = {
      getItem: (key: string): string | null => {
        return key in store ? store[key] : null;
      },
      setItem: (key: string, value: string) => {
        store[key] = `${value}`;
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        store = {};
      }
    };

    spyOn(localStorage, 'getItem').and.callFake(mockLocalStorage.getItem);
    spyOn(localStorage, 'setItem').and.callFake(mockLocalStorage.setItem);
    spyOn(localStorage, 'removeItem').and.callFake(mockLocalStorage.removeItem);
    spyOn(localStorage, 'clear').and.callFake(mockLocalStorage.clear);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('Service initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should initialize metadata on creation', () => {
      let metadata = null;
      service.metadata$.subscribe((data) => {
        metadata = data;
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/metadata`);
      expect(req.request.method).toBe('GET');
      req.flush(mockMetadata);

      expect(metadata).toEqual(mockMetadata);
    });
  });

  describe('getTransactionMetadata', () => {
    it('should fetch transaction metadata', () => {
      service.getTransactionMetadata().subscribe((metadata) => {
        expect(metadata).toEqual(mockMetadata);
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/metadata`);
      expect(req.request.method).toBe('GET');
      req.flush(mockMetadata);
    });

    it('should include Authorization header', () => {
      localStorage.setItem('access_token', 'mock-token');
      service.getTransactionMetadata().subscribe();

      const req = httpMock.expectOne(`${service['apiUrl']}/metadata`);
      expect(req.request.headers.get('Authorization')).toBe('Bearer mock-token');
      req.flush(mockMetadata);
    });
  });

  describe('createTransaction', () => {
    it('should create a single transaction', () => {
      service.createTransaction(mockTransaction).subscribe((response) => {
        expect(response).toEqual(mockTransaction);
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(mockTransaction);
      req.flush(mockTransaction);
    });

    it('should handle creation errors', () => {
      service.createTransaction(mockTransaction).subscribe(
        () => fail('should have failed'),
        (error) => {
          expect(error).toBeTruthy();
        }
      );

      const req = httpMock.expectOne(`${service['apiUrl']}/`);
      req.flush({ detail: 'Invalid transaction data' }, { status: 400, statusText: 'Bad Request' });
    });
  });

  describe('bulkCreateTransactions', () => {
    it('should bulk create transactions', () => {
      const bulkRequest = {
        transactions: [mockTransaction],
        filename: 'test.csv',
        allow_duplicates: false
      };

      const mockResponse: BulkUploadResponse = {
        bulk_upload_id: 1,
        total_rows: 1,
        successful_count: 1,
        failed_count: 0,
        duplicate_count: 0,
        status: 'COMPLETED',
        created_transactions: [mockTransaction],
        failed_rows: []
      };

      service.bulkCreateTransactions(bulkRequest).subscribe((response) => {
        expect(response).toEqual(mockResponse);
        expect(response.successful_count).toBe(1);
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/bulk`);
      expect(req.request.method).toBe('POST');
      req.flush(mockResponse);
    });

    it('should handle bulk upload with duplicates', () => {
      const bulkRequest = {
        transactions: [mockTransaction, mockTransaction],
        filename: 'test.csv',
        allow_duplicates: false
      };

      const mockResponse: BulkUploadResponse = {
        bulk_upload_id: 1,
        total_rows: 2,
        successful_count: 1,
        failed_count: 0,
        duplicate_count: 1,
        status: 'PENDING_REVIEW',
        created_transactions: [mockTransaction],
        failed_rows: []
      };

      service.bulkCreateTransactions(bulkRequest).subscribe((response) => {
        expect(response.status).toBe('PENDING_REVIEW');
        expect(response.duplicate_count).toBe(1);
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/bulk`);
      req.flush(mockResponse);
    });
  });

  describe('updateTransaction', () => {
    it('should update a transaction', () => {
      const updateData = {
        amount: 50.00,
        merchant: 'Trader Joe\'s'
      };

      const updatedTransaction = { ...mockTransaction, ...updateData };

      service.updateTransaction(1, updateData).subscribe((response) => {
        expect(response.amount).toBe(50.00);
        expect(response.merchant).toBe('Trader Joe\'s');
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/1`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.body).toEqual(updateData);
      req.flush(updatedTransaction);
    });
  });

  describe('deleteTransaction', () => {
    it('should delete a transaction', () => {
      service.deleteTransaction(1).subscribe((response) => {
        expect(response.message).toContain('deleted');
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'Transaction deleted successfully' });
    });
  });

  describe('getBulkUploadStatus', () => {
    it('should get bulk upload status', () => {
      const mockStatus = {
        bulk_upload_id: 1,
        filename: 'test.csv',
        total_rows: 10,
        successful_count: 9,
        failed_count: 1,
        duplicate_count: 0,
        status: 'COMPLETED',
        uploaded_at: '2025-10-11T15:30:00Z',
        processed_at: '2025-10-11T15:31:00Z'
      };

      service.getBulkUploadStatus(1).subscribe((response) => {
        expect(response.bulk_upload_id).toBe(1);
        expect(response.successful_count).toBe(9);
      });

      const req = httpMock.expectOne(`${service['apiUrl']}/bulk/1`);
      expect(req.request.method).toBe('GET');
      req.flush(mockStatus);
    });
  });

  describe('CSV Parsing', () => {
    it('should parse valid CSV file', async () => {
      const csvContent = `date,description,amount,currency,transaction_type_id,payment_method_id,card_id
2025-10-15,Groceries,45.99,USD,1,1,1
2025-10-14,Gas,55.00,USD,1,1,1`;

      const file = new File([csvContent], 'test.csv', { type: 'text/csv' });

      const transactions = await service.parseCSVFile(file);
      expect(transactions.length).toBe(2);
      expect(transactions[0].amount).toBe(45.99);
      expect(transactions[0].currency).toBe('USD');
    });

    it('should reject CSV with missing required columns', async () => {
      const csvContent = `date,amount
2025-10-15,45.99`;

      const file = new File([csvContent], 'test.csv', { type: 'text/csv' });

      try {
        await service.parseCSVFile(file);
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.message).toContain('Missing required');
      }
    });

    it('should reject CSV with insufficient rows', async () => {
      const csvContent = `date,description,amount,currency,transaction_type_id,payment_method_id,card_id`;

      const file = new File([csvContent], 'test.csv', { type: 'text/csv' });

      try {
        await service.parseCSVFile(file);
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.message).toContain('at least');
      }
    });
  });

  describe('Transaction Validation', () => {
    it('should validate transaction date', () => {
      const transaction = { ...mockTransaction, date: '2099-01-01' };
      const error = service.validateTransaction(transaction);
      expect(error).toContain('future');
    });

    it('should validate amount is positive', () => {
      const transaction = { ...mockTransaction, amount: -10 };
      const error = service.validateTransaction(transaction);
      expect(error).toContain('positive');
    });

    it('should validate currency', () => {
      const transaction = { ...mockTransaction, currency: 'EUR' as any };
      const error = service.validateTransaction(transaction);
      expect(error).toContain('USD or CAD');
    });

    it('should validate required fields', () => {
      const transaction = { ...mockTransaction, description: '' };
      const error = service.validateTransaction(transaction);
      expect(error).toContain('required');
    });

    it('should pass validation for valid transaction', () => {
      const error = service.validateTransaction(mockTransaction);
      expect(error).toBeNull();
    });
  });

  describe('CSV Template Generation', () => {
    it('should generate CSV template', () => {
      const template = service.generateCSVTemplate();
      expect(template).toContain('date');
      expect(template).toContain('description');
      expect(template).toContain('2025-10-15');
    });

    it('should have correct number of example rows', () => {
      const template = service.generateCSVTemplate();
      const lines = template.split('\n');
      // 1 header + 3 example rows = 4 lines
      expect(lines.length).toBeGreaterThanOrEqual(4);
    });
  });

  describe('Utility Methods', () => {
    it('should format date correctly', () => {
      const formatted = service.formatDate('2025-10-15');
      expect(formatted).toContain('2025');
    });

    it('should format currency correctly', () => {
      const formatted = service.formatCurrency(45.99, 'USD');
      expect(formatted).toContain('45.99');
    });

    it('should get category by ID', () => {
      service.metadata$.next(mockMetadata);
      const category = service.getCategoryById(1);
      expect(category?.name).toBe('Food & Dining');
    });

    it('should get payment method by ID', () => {
      service.metadata$.next(mockMetadata);
      const method = service.getPaymentMethodById(1);
      expect(method?.name).toBe('Credit Card');
    });
  });

  describe('Caching', () => {
    it('should cache metadata', () => {
      spyOn(cacheService, 'get').and.returnValue(mockMetadata);
      spyOn(cacheService, 'set');

      service['loadMetadata']();

      expect(cacheService.get).toHaveBeenCalledWith('transaction_metadata');
    });

    it('should invalidate cache on transaction creation', () => {
      spyOn(cacheService, 'remove');

      service.createTransaction(mockTransaction).subscribe();

      const req = httpMock.expectOne(`${service['apiUrl']}/`);
      req.flush(mockTransaction);

      expect(cacheService.remove).toHaveBeenCalledWith('transaction_metadata');
    });
  });
});
