import { Component, EventEmitter, Input, Output, OnInit, OnChanges, SimpleChanges, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridApi, GridReadyEvent, ICellEditorParams, ICellRendererParams, ModuleRegistry, AllCommunityModule, GridOptions } from 'ag-grid-community';
import { ThemeService, Theme } from '../../services/theme.service';
import { ManualTransactionService, ManualTransaction as ServiceManualTransaction, TransactionMetadata, MetadataItem } from '../../services/manual-transaction.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { DuplicateConfirmationComponent } from './duplicate-confirmation.component';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  bgColor: string;
}

export interface Subcategory {
  id: number;
  name: string;
  categoryId: number;
}

export interface BudgetType {
  id: number;
  name: string;
  description: string;
}

export interface BankType {
  id: number;
  name: string;
  icon: string;
}

export interface Card {
  id: number;
  name: string;
  bankTypeId: number;
  lastFourDigits: string;
}

export interface ManualTransaction {
  id?: string;
  date: Date;
  categoryId: number;
  amount: number;
  description: string;
  merchant: string;
  subcategoryId?: number;
  budgetTypeId?: number;
  bankTypeId?: number;
  cardId?: number;
}

@Component({
  selector: 'app-manual-transaction-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, AgGridModule, MatDialogModule],
  templateUrl: './manual-transaction-modal.component.html',
  styleUrls: ['./manual-transaction-modal.component.scss']
})
export class ManualTransactionModalComponent implements OnInit, OnChanges, OnDestroy {
  @Input() isOpen = false;
  @Output() closeModal = new EventEmitter<void>();
  @Output() transactionsSaved = new EventEmitter<ManualTransaction[]>();

  public gridApi!: GridApi;
  rowData: ServiceManualTransaction[] = [];
  columnDefs: ColDef[] = [];
  private gridInitialized = false;
  currentTheme: Theme = 'light';
  private destroy$ = new Subject<void>();

  // UI state
  activeTab: 'manual' | 'csv' = 'manual';
  isSaving = false;
  csvUploading = false;
  csvFileName = '';
  csvError: string | null = null;
  csvSuccess = false;
  csvTransactionCount = 0;
  isDraggingCSV = false;
  toastMessage: string | null = null;
  toastType: 'success' | 'error' | 'warning' | null = null;

  // Metadata from service
  metadata: TransactionMetadata | null = null;
  categories: MetadataItem[] = [];
  paymentMethods: MetadataItem[] = [];
  budgetTypes: MetadataItem[] = [];
  transactionTypes: MetadataItem[] = [];

  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
    editable: true
  };

  // AG Grid v33+ theme configuration
  gridOptions: GridOptions = {
    // Dark mode support
    domLayout: 'normal',
    animateRows: true,
    rowSelection: 'multiple',
    suppressRowClickSelection: true,
    enableRangeSelection: true,
    enableFillHandle: true,
    enableCellTextSelection: true,
    suppressCopyRowsToClipboard: false
  };

  constructor(
    private fb: FormBuilder,
    private themeService: ThemeService,
    private manualTransactionService: ManualTransactionService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    // Load metadata from service
    this.manualTransactionService.metadata$
      .pipe(takeUntil(this.destroy$))
      .subscribe((metadata) => {
        if (metadata) {
          this.metadata = metadata;
          this.categories = metadata.expense_categories;
          this.paymentMethods = metadata.payment_methods;
          this.budgetTypes = metadata.budget_types;
          this.transactionTypes = metadata.transaction_types;
          // Reinitialize columns when metadata loads
          this.initializeColumnDefs();
        }
      });

    // Subscribe to theme changes
    this.themeService.currentTheme$
      .pipe(takeUntil(this.destroy$))
      .subscribe(theme => {
        this.currentTheme = theme;
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // Add method to handle modal opening
  ngOnChanges(changes: SimpleChanges): void {
    console.log('ngOnChanges called:', changes);
    if (changes['isOpen']) {
      console.log('isOpen changed to:', this.isOpen);
      if (this.isOpen) {
        // Modal is opening
        console.log('Modal is opening, current rowData length:', this.rowData.length);
        // Reset data and flags when modal opens
        this.rowData = [];
        this.gridInitialized = false;
        // Don't add row here, let onGridReady handle it
      } else {
        // Modal is closing, reset the data
        console.log('Modal is closing, resetting data');
        this.rowData = [];
        this.gridInitialized = false;
        if (this.gridApi) {
          this.gridApi.applyTransaction({ remove: this.gridApi.getRenderedNodes().map(node => node.data) });
        }
      }
    }
  }

  initializeColumnDefs(): void {
    this.columnDefs = [
      {
        headerName: 'Date',
        field: 'date',
        cellEditor: 'agDateCellEditor',
        cellEditorParams: {
          browserDatePicker: true
        },
        valueFormatter: (params) => {
          if (params.value) {
            const date = typeof params.value === 'string' ? new Date(params.value) : params.value;
            return date.toLocaleDateString();
          }
          return '';
        },
        width: 120
      },
      {
        headerName: 'Amount',
        field: 'amount',
        cellEditor: 'agNumberCellEditor',
        cellEditorParams: {
          precision: 2,
          step: 0.01
        },
        valueFormatter: (params) => {
          if (params.value) {
            return `$${parseFloat(params.value).toFixed(2)}`;
          }
          return '';
        },
        width: 100
      },
      {
        headerName: 'Currency',
        field: 'currency',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: ['USD', 'CAD']
        },
        width: 100
      },
      {
        headerName: 'Description',
        field: 'description',
        cellEditor: 'agTextCellEditor',
        width: 200
      },
      {
        headerName: 'Merchant',
        field: 'merchant',
        cellEditor: 'agTextCellEditor',
        width: 150
      },
      {
        headerName: 'Transaction Type',
        field: 'transaction_type_id',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.transactionTypes.map(t => t.name)
        },
        valueGetter: (params) => {
          const type = this.transactionTypes.find(t => t.id === params.data.transaction_type_id);
          return type ? type.name : '';
        },
        valueSetter: (params) => {
          const type = this.transactionTypes.find(t => t.name === params.newValue);
          if (type) {
            params.data.transaction_type_id = type.id;
            return true;
          }
          return false;
        },
        width: 130
      },
      {
        headerName: 'Category',
        field: 'expense_category_id',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.categories.map(cat => cat.name)
        },
        valueGetter: (params) => {
          const category = this.categories.find(cat => cat.id === params.data.expense_category_id);
          return category ? category.name : '';
        },
        valueSetter: (params) => {
          const category = this.categories.find(cat => cat.name === params.newValue);
          if (category) {
            params.data.expense_category_id = category.id;
            return true;
          }
          return false;
        },
        width: 150
      },
      {
        headerName: 'Payment Method',
        field: 'payment_method_id',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.paymentMethods.map(pm => pm.name)
        },
        valueGetter: (params) => {
          const method = this.paymentMethods.find(m => m.id === params.data.payment_method_id);
          return method ? method.name : '';
        },
        valueSetter: (params) => {
          const method = this.paymentMethods.find(m => m.name === params.newValue);
          if (method) {
            params.data.payment_method_id = method.id;
            return true;
          }
          return false;
        },
        width: 150
      },
      {
        headerName: 'Budget Type',
        field: 'budget_type_id',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.budgetTypes.map(budget => budget.name)
        },
        valueGetter: (params) => {
          const budgetType = this.budgetTypes.find(budget => budget.id === params.data.budget_type_id);
          return budgetType ? budgetType.name : '';
        },
        valueSetter: (params) => {
          const budgetType = this.budgetTypes.find(budget => budget.name === params.newValue);
          if (budgetType) {
            params.data.budget_type_id = budgetType.id;
            return true;
          }
          return false;
        },
        width: 120
      },
      {
        headerName: 'Shared',
        field: 'is_shared',
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: ['true', 'false']
        },
        valueGetter: (params) => {
          return params.data.is_shared ? 'true' : 'false';
        },
        valueSetter: (params) => {
          params.data.is_shared = params.newValue === 'true';
          return true;
        },
        width: 80
      },
      {
        headerName: 'Actions',
        cellRenderer: (params: ICellRendererParams) => {
          const button = document.createElement('button');
          button.className = 'text-red-600 hover:text-red-800 px-2 py-1 rounded';
          button.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
          `;
          button.addEventListener('click', () => {
            if (params.node?.id) {
              this.deleteRow(params.node.id);
            }
          });
          return button;
        },
        width: 80,
        sortable: false,
        filter: false,
        editable: false
      }
    ];
  }

  onGridReady(params: GridReadyEvent): void {
    console.log('Grid is ready, initialized:', this.gridInitialized);
    this.gridApi = params.api;
    
    // Only add initial empty row if grid hasn't been initialized yet
    if (!this.gridInitialized) {
      console.log('Grid ready, adding initial row');
      this.gridInitialized = true;
      this.addEmptyRow();
    }
  }

  addEmptyRow(): void {
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0]; // YYYY-MM-DD format

    const newTransaction: ServiceManualTransaction = {
      date: dateStr,
      amount: 0,
      currency: 'USD',
      description: '',
      merchant: '',
      notes: '',
      transaction_type_id: 0,
      expense_category_id: undefined,
      expense_subcategory_id: undefined,
      payment_method_id: 0,
      budget_type_id: undefined,
      card_id: 0,
      is_shared: false
    };

    this.rowData.push(newTransaction);

    if (this.gridApi) {
      this.gridApi.applyTransaction({ add: [newTransaction] });
    }
  }

  deleteRow(rowId: string): void {
    const rowToDelete = this.rowData.find(row => row.id === rowId);
    if (rowToDelete) {
      this.rowData = this.rowData.filter(row => row.id !== rowId);
      if (this.gridApi) {
        this.gridApi.applyTransaction({ remove: [rowToDelete] });
      }
    }
  }



  onSave(): void {
    // Get all data from grid
    const allData: ServiceManualTransaction[] = [];
    this.gridApi.forEachNode((node) => {
      if (node.data) {
        allData.push(node.data);
      }
    });

    // Validate transactions
    const validationErrors: Array<{ index: number; error: string }> = [];
    const validTransactions: ServiceManualTransaction[] = [];

    allData.forEach((transaction, index) => {
      // Only validate non-empty rows
      if (transaction.amount === 0 && !transaction.description.trim()) {
        return; // Skip empty rows
      }

      const error = this.manualTransactionService.validateTransaction(transaction);
      if (error) {
        validationErrors.push({ index, error });
      } else {
        validTransactions.push(transaction);
      }
    });

    // Show validation errors if any
    if (validationErrors.length > 0) {
      const errorMessages = validationErrors.map(e => `Row ${e.index + 1}: ${e.error}`).join('\n');
      this.showToast(`Validation errors:\n${errorMessages}`, 'error');
      return;
    }

    if (validTransactions.length === 0) {
      this.showToast('Please add at least one valid transaction before saving.', 'warning');
      return;
    }

    this.isSaving = true;

    if (validTransactions.length === 1) {
      // Single transaction
      this.saveSingleTransaction(validTransactions[0]);
    } else {
      // Bulk transactions
      this.saveBulkTransactions(validTransactions);
    }
  }

  private saveSingleTransaction(transaction: ServiceManualTransaction): void {
    this.manualTransactionService.createTransaction(transaction)
      .pipe(takeUntil(this.destroy$))
      .subscribe(
        (response) => {
          this.isSaving = false;
          this.showToast('Transaction saved successfully!', 'success');
          this.transactionsSaved.emit([transaction]);
          this.onCancel();
        },
        (error) => {
          this.isSaving = false;
          this.showToast(`Error saving transaction: ${error.message}`, 'error');
        }
      );
  }

  private saveBulkTransactions(transactions: ServiceManualTransaction[]): void {
    const request = {
      transactions,
      filename: 'manual_upload.csv'
    };

    this.manualTransactionService.bulkCreateTransactions(request)
      .pipe(takeUntil(this.destroy$))
      .subscribe(
        (response) => {
          this.isSaving = false;

          if (response.duplicate_count > 0 && response.status === 'PENDING_REVIEW') {
            // Show duplicate confirmation dialog
            this.openDuplicateDialog(response);
          } else {
            this.showToast(`${response.successful_count} transaction(s) saved successfully!`, 'success');
            this.transactionsSaved.emit(response.created_transactions);
            this.onCancel();
          }
        },
        (error) => {
          this.isSaving = false;
          this.showToast(`Error saving transactions: ${error.message}`, 'error');
        }
      );
  }

  private openDuplicateDialog(response: any): void {
    const dialogRef = this.dialog.open(DuplicateConfirmationComponent, {
      width: '600px',
      data: response
    });

    dialogRef.afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe((result) => {
        if (result) {
          this.confirmDuplicates(result);
        } else {
          this.rowData = [];
          if (this.gridApi) {
            this.gridApi.setRowData([]);
          }
          this.showToast('Duplicate handling cancelled', 'info');
        }
      });
  }

  private confirmDuplicates(result: any): void {
    const confirmRequest = {
      duplicate_transaction_ids: result.duplicateIds,
      action: result.action,
      user_notes: result.userNotes
    };

    this.manualTransactionService.confirmDuplicateHandling(confirmRequest)
      .pipe(takeUntil(this.destroy$))
      .subscribe(
        (response) => {
          this.showToast(`Duplicates ${result.action.toLowerCase()}ed successfully!`, 'success');
          this.rowData = [];
          if (this.gridApi) {
            this.gridApi.setRowData([]);
          }
          this.transactionsSaved.emit([]);
          this.onCancel();
        },
        (error) => {
          this.showToast(`Error confirming duplicates: ${error.message}`, 'error');
        }
      );
  }

  onCancel(): void {
    this.closeModal.emit();
  }

  private showToast(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    this.toastMessage = message;
    this.toastType = type as 'success' | 'error' | 'warning';
    setTimeout(() => {
      this.toastMessage = null;
      this.toastType = null;
    }, 5000);
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.onCancel();
    }
  }

  // CSV Upload Methods
  onCSVFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    const files = target.files;

    if (files && files.length > 0) {
      const file = files[0];
      this.processCSVFile(file);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingCSV = true;
  }

  onDropCSV(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDraggingCSV = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        this.processCSVFile(file);
      } else {
        this.showToast('Please drop a CSV file', 'error');
      }
    }
  }

  private async processCSVFile(file: File): Promise<void> {
    this.csvUploading = true;
    this.csvFileName = file.name;
    this.csvError = null;
    this.csvSuccess = false;
    this.csvTransactionCount = 0;

    try {
      const transactions = await this.manualTransactionService.parseCSVFile(file);
      this.csvTransactionCount = transactions.length;

      // Add transactions to grid
      this.rowData = [...this.rowData, ...transactions];
      if (this.gridApi) {
        this.gridApi.applyTransaction({ add: transactions });
      }

      this.csvSuccess = true;
      this.showToast(`Successfully loaded ${transactions.length} transaction(s) from CSV`, 'success');

      // Switch to manual entry tab to show the loaded transactions
      setTimeout(() => {
        this.activeTab = 'manual';
      }, 500);
    } catch (error: any) {
      this.csvError = error.message || 'Failed to parse CSV file';
      this.showToast(this.csvError, 'error');
    } finally {
      this.csvUploading = false;
    }
  }

  downloadCSVTemplate(): void {
    this.manualTransactionService.downloadCSVTemplate();
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }
}
