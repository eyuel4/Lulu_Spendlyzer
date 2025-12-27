import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID, ViewChild } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridApi, GridOptions, GridReadyEvent, ICellEditorParams, ICellRendererParams } from 'ag-grid-community';
import { TransactionService, Transaction, TransactionFilters, DropdownMetadata, TransactionUpdate } from '../../services/transaction.service';
import { PlaidService, PlaidAccount } from '../../services/plaid.service';
import { ThemeService } from '../../services/theme.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-transactions-list',
  standalone: true,
  imports: [CommonModule, FormsModule, AgGridAngular, RouterModule],
  templateUrl: './transactions-list.component.html',
  styleUrls: ['./transactions-list.component.scss']
})
export class TransactionsListComponent implements OnInit, OnDestroy {
  transactions: Transaction[] = [];
  filteredTransactions: Transaction[] = [];
  isLoading = false;
  error: string | null = null;
  
  // Filters
  filters: TransactionFilters = {
    skip: 0,
    limit: 100
  };
  
  // Filter options
  connectedBanks: PlaidAccount[] = [];
  selectedBankId: number | null = null;
  selectedCardId: number | null = null;
  merchantSearch: string = '';
  categorySearch: string = '';
  startDate: string = '';
  endDate: string = '';
  selectedCurrency: string = '';
  
  // Pagination
  currentPage = 1;
  pageSize = 50;
  totalTransactions = 0;
  
  // Dropdown metadata
  dropdownMetadata: DropdownMetadata | null = null;
  
  // Theme
  currentTheme: 'light' | 'dark' = 'light';
  
  // AG Grid
  @ViewChild(AgGridAngular) agGrid!: AgGridAngular;
  gridApi!: GridApi;
  columnDefs: ColDef[] = [
    { 
      field: 'date', 
      headerName: 'Date', 
      sortable: true, 
      filter: true, 
      width: 120,
      editable: false,
      valueFormatter: (params: any) => {
        if (!params.value) return '';
        return new Date(params.value).toLocaleDateString();
      }
    },
    { 
      field: 'bank_name', 
      headerName: 'Bank', 
      sortable: true, 
      filter: true, 
      width: 150,
      editable: false
    },
    { 
      field: 'card_name', 
      headerName: 'Card', 
      sortable: true, 
      filter: true, 
      width: 150,
      editable: false
    },
    { 
      field: 'merchant_name', 
      headerName: 'Merchant', 
      sortable: true, 
      filter: true, 
      width: 200,
      editable: false
    },
    { 
      field: 'expense_category_name', 
      headerName: 'Category', 
      sortable: true, 
      filter: true, 
      width: 150,
      editable: false,
      valueGetter: (params: any) => {
        return params.data?.expense_category_name || params.data?.custom_category || params.data?.plaid_category || 'Uncategorized';
      }
    },
    { 
      field: 'custom_category', 
      headerName: 'Custom Category', 
      sortable: true, 
      filter: true, 
      width: 150,
      editable: false
    },
    { 
      field: 'amount', 
      headerName: 'Amount', 
      sortable: true, 
      filter: true, 
      width: 120,
      editable: false,
      cellRenderer: (params: any) => {
        const amount = params.value || 0;
        const currency = params.data?.currency || 'USD';
        const isExpense = amount < 0;
        const color = isExpense ? 'text-red-600' : 'text-green-600';
        const prefix = isExpense ? '-' : '+';
        return `<span class="${color} font-semibold">${prefix}${currency} ${Math.abs(amount).toFixed(2)}</span>`;
      }
    },
    { 
      field: 'currency', 
      headerName: 'Currency', 
      sortable: true, 
      filter: true, 
      width: 100,
      editable: false
    }
  ];
  
  gridOptions: GridOptions = {
    domLayout: 'normal',
    animateRows: true,
    rowSelection: 'single',
    suppressHorizontalScroll: false,
    getRowId: (params: any) => params.data.id.toString()
  };
  
  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true
  };
  
  private destroy$ = new Subject<void>();

  constructor(
    private transactionService: TransactionService,
    private plaidService: PlaidService,
    private themeService: ThemeService,
    public router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      // Subscribe to theme changes
      this.themeService.currentTheme$
        .pipe(takeUntil(this.destroy$))
        .subscribe(theme => {
          this.currentTheme = theme;
        });
      
      this.loadConnectedBanks();
      this.loadDropdownMetadata();
      this.loadTransactions();
    }
  }

  loadDropdownMetadata() {
    this.transactionService.getDropdownMetadata()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (metadata) => {
          this.dropdownMetadata = metadata;
          this.initializeColumnDefs();
          // Refresh grid if it's already initialized
          if (this.gridApi) {
            this.gridApi.setColumnDefs(this.columnDefs);
          }
        },
        error: (err) => {
          console.error('Error loading dropdown metadata:', err);
          // Grid will still work with basic columns
        }
      });
  }

  initializeColumnDefs() {
    if (!this.dropdownMetadata) return;

    this.columnDefs = [
      { 
        field: 'date', 
        headerName: 'Date', 
        sortable: true, 
        filter: true, 
        width: 120,
        editable: false,
        valueFormatter: (params: any) => {
          if (!params.value) return '';
          return new Date(params.value).toLocaleDateString();
        }
      },
      { 
        field: 'bank_name', 
        headerName: 'Bank', 
        sortable: true, 
        filter: true, 
        width: 150,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.dropdownMetadata.banks.map(b => b.name)
        },
        onCellValueChanged: (params: any) => {
          if (params.oldValue !== params.newValue && params.newValue) {
            const bank = this.dropdownMetadata?.banks.find(b => b.name === params.newValue);
            if (bank) {
              // Find the first card for this bank and update transaction
              const card = this.dropdownMetadata?.cards.find(c => c.bank_name === bank.name);
              if (card) {
                this.updateTransactionField(params.data.id, { card_id: card.id });
              }
            }
          }
        }
      },
      { 
        field: 'card_name', 
        headerName: 'Card', 
        sortable: true, 
        filter: true, 
        width: 150,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: (params: any) => {
          const bankName = params.data?.bank_name;
          const cardsForBank = bankName 
            ? this.dropdownMetadata?.cards.filter(c => c.bank_name === bankName) || []
            : this.dropdownMetadata?.cards || [];
          return {
            values: cardsForBank.map(c => `${c.name} •••• ${c.last4}`)
          };
        },
        onCellValueChanged: (params: any) => {
          if (params.oldValue !== params.newValue) {
            const cardName = params.newValue?.split(' •••• ')[0];
            const card = this.dropdownMetadata?.cards.find(c => c.name === cardName);
            if (card) {
              this.updateTransactionField(params.data.id, { card_id: card.id });
            }
          }
        }
      },
      { 
        field: 'merchant_name', 
        headerName: 'Merchant', 
        sortable: true, 
        filter: true, 
        width: 200,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.dropdownMetadata.merchants,
          allowTyping: true
        },
        onCellValueChanged: (params: any) => {
          if (params.oldValue !== params.newValue) {
            this.updateTransactionField(params.data.id, { merchant_name: params.newValue || null });
          }
        }
      },
      { 
        field: 'expense_category_name', 
        headerName: 'Category', 
        sortable: true, 
        filter: true, 
        width: 150,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.dropdownMetadata.expense_categories.map(c => c.name)
        },
        valueGetter: (params: any) => {
          return params.data?.expense_category_name || params.data?.custom_category || params.data?.plaid_category || 'Uncategorized';
        },
        onCellValueChanged: (params: any) => {
          if (params.oldValue !== params.newValue) {
            const category = this.dropdownMetadata?.expense_categories.find(c => c.name === params.newValue);
            if (category) {
              this.updateTransactionField(params.data.id, { 
                expense_category_id: category.id,
                custom_category: null // Clear custom category when setting expense category
              });
            }
          }
        }
      },
      { 
        field: 'custom_category', 
        headerName: 'Custom Category', 
        sortable: true, 
        filter: true, 
        width: 150,
        editable: true,
        cellEditor: 'agSelectCellEditor',
        cellEditorParams: {
          values: this.dropdownMetadata.custom_categories,
          allowTyping: true
        },
        onCellValueChanged: (params: any) => {
          if (params.oldValue !== params.newValue) {
            this.updateTransactionField(params.data.id, { 
              custom_category: params.newValue || null,
              expense_category_id: null // Clear expense category when setting custom category
            });
          }
        }
      },
      { 
        field: 'amount', 
        headerName: 'Amount', 
        sortable: true, 
        filter: true, 
        width: 120,
        editable: false,
        cellRenderer: (params: any) => {
          const amount = params.value || 0;
          const currency = params.data?.currency || 'USD';
          const isExpense = amount < 0;
          const color = isExpense ? 'text-red-600' : 'text-green-600';
          const prefix = isExpense ? '-' : '+';
          return `<span class="${color} font-semibold">${prefix}${currency} ${Math.abs(amount).toFixed(2)}</span>`;
        }
      },
      { 
        field: 'currency', 
        headerName: 'Currency', 
        sortable: true, 
        filter: true, 
        width: 100,
        editable: false
      }
    ];
    
    // Refresh grid if already initialized
    if (this.gridApi) {
      this.gridApi.setColumnDefs(this.columnDefs);
    }
  }

  updateTransactionField(transactionId: number, updates: TransactionUpdate) {
    this.transactionService.updateTransaction(transactionId, updates)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (updatedTransaction) => {
          // Update the row data
          const rowNode = this.gridApi.getRowNode(transactionId.toString());
          if (rowNode) {
            // Update the data object with new values
            const updatedData = {
              ...rowNode.data,
              ...updates,
              // Preserve relationship fields from updated transaction
              bank_name: updatedTransaction.bank_name || rowNode.data.bank_name,
              card_name: updatedTransaction.card_name || rowNode.data.card_name,
              expense_category_name: updatedTransaction.expense_category_name || rowNode.data.expense_category_name,
              expense_category_id: updatedTransaction.expense_category_id || rowNode.data.expense_category_id
            };
            rowNode.setData(updatedData);
          }
        },
        error: (err) => {
          console.error('Error updating transaction:', err);
          // Revert the change by refreshing the grid
          this.loadTransactions();
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadConnectedBanks() {
    this.plaidService.getConnectedAccounts()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (banks) => {
          this.connectedBanks = banks;
        },
        error: (err) => {
          console.error('Error loading banks:', err);
        }
      });
  }

  loadTransactions() {
    this.isLoading = true;
    this.error = null;

    // Build filters
    const filters: TransactionFilters = {
      skip: (this.currentPage - 1) * this.pageSize,
      limit: this.pageSize
    };

    if (this.selectedCardId) filters.card_id = this.selectedCardId;
    if (this.selectedBankId) {
      const bank = this.connectedBanks.find(b => b.id === this.selectedBankId);
      if (bank) filters.bank_name = bank.bank_name;
    }
    if (this.merchantSearch) filters.merchant_name = this.merchantSearch;
    if (this.categorySearch) filters.custom_category = this.categorySearch;
    if (this.startDate) filters.start_date = this.startDate;
    if (this.endDate) filters.end_date = this.endDate;
    if (this.selectedCurrency) filters.currency = this.selectedCurrency;

    this.transactionService.getTransactions(filters)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (transactions) => {
          this.transactions = transactions;
          this.filteredTransactions = transactions;
          this.totalTransactions = transactions.length; // Note: API should return total count
          this.isLoading = false;
          
          // Initialize column defs with dropdowns if metadata is loaded
          if (this.dropdownMetadata) {
            this.initializeColumnDefs();
            // Update grid columns if already initialized
            if (this.gridApi) {
              this.gridApi.setColumnDefs(this.columnDefs);
            }
          }
        },
        error: (err) => {
          console.error('Error loading transactions:', err);
          this.error = 'Failed to load transactions. Please try again.';
          this.isLoading = false;
        }
      });
  }

  applyFilters() {
    this.currentPage = 1;
    this.loadTransactions();
  }

  clearFilters() {
    this.selectedBankId = null;
    this.selectedCardId = null;
    this.merchantSearch = '';
    this.categorySearch = '';
    this.startDate = '';
    this.endDate = '';
    this.selectedCurrency = '';
    this.applyFilters();
  }

  onBankChange() {
    // Reset card selection when bank changes
    this.selectedCardId = null;
    this.applyFilters();
  }

  onGridReady(params: GridReadyEvent) {
    this.gridApi = params.api;
    // If metadata is already loaded, update columns
    if (this.dropdownMetadata) {
      this.initializeColumnDefs();
      this.gridApi.setColumnDefs(this.columnDefs);
    }
  }

  getCardsForSelectedBank(): PlaidAccount[] {
    if (!this.selectedBankId) return [];
    return this.connectedBanks.filter(bank => bank.id === this.selectedBankId);
  }

  goToPage(page: number) {
    if (page >= 1 && page <= Math.ceil(this.totalTransactions / this.pageSize)) {
      this.currentPage = page;
      this.loadTransactions();
    }
  }

  get totalPages(): number {
    return Math.ceil(this.totalTransactions / this.pageSize);
  }
}

