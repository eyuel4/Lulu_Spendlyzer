import { Component, EventEmitter, Input, Output, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AgGridModule } from 'ag-grid-angular';
import { ColDef, GridApi, GridReadyEvent, ICellEditorParams, ICellRendererParams, ModuleRegistry, AllCommunityModule, GridOptions } from 'ag-grid-community';
import { ThemeService, Theme } from '../../services/theme.service';

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
  imports: [CommonModule, FormsModule, ReactiveFormsModule, AgGridModule],
  templateUrl: './manual-transaction-modal.component.html',
  styleUrls: ['./manual-transaction-modal.component.scss']
})
export class ManualTransactionModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Output() closeModal = new EventEmitter<void>();
  @Output() transactionsSaved = new EventEmitter<ManualTransaction[]>();

  public gridApi!: GridApi;
  rowData: ManualTransaction[] = [];
  columnDefs: ColDef[] = [];
  private gridInitialized = false;
  currentTheme: Theme = 'light';

  // Sample data - in real app, these would come from services
  categories: Category[] = [
    {
      id: 1,
      name: 'Food & Dining',
      icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1',
      color: 'text-orange-600',
      bgColor: 'bg-orange-100'
    },
    {
      id: 2,
      name: 'Transportation',
      icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      id: 3,
      name: 'Shopping',
      icon: 'M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100'
    },
    {
      id: 4,
      name: 'Entertainment',
      icon: 'M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
      color: 'text-green-600',
      bgColor: 'bg-green-100'
    },
    {
      id: 5,
      name: 'Healthcare',
      icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
      color: 'text-red-600',
      bgColor: 'bg-red-100'
    },
    {
      id: 6,
      name: 'Utilities',
      icon: 'M13 10V3L4 14h7v7l9-11h-7z',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100'
    }
  ];

  subcategories: Subcategory[] = [
    { id: 1, name: 'Groceries', categoryId: 1 },
    { id: 2, name: 'Restaurants', categoryId: 1 },
    { id: 3, name: 'Fast Food', categoryId: 1 },
    { id: 4, name: 'Gas', categoryId: 2 },
    { id: 5, name: 'Public Transport', categoryId: 2 },
    { id: 6, name: 'Uber/Lyft', categoryId: 2 },
    { id: 7, name: 'Clothing', categoryId: 3 },
    { id: 8, name: 'Electronics', categoryId: 3 },
    { id: 9, name: 'Movies', categoryId: 4 },
    { id: 10, name: 'Games', categoryId: 4 },
    { id: 11, name: 'Doctor Visit', categoryId: 5 },
    { id: 12, name: 'Medication', categoryId: 5 },
    { id: 13, name: 'Electricity', categoryId: 6 },
    { id: 14, name: 'Water', categoryId: 6 },
    { id: 15, name: 'Internet', categoryId: 6 }
  ];

  budgetTypes: BudgetType[] = [
    { id: 1, name: 'Essential', description: 'Necessary expenses like food, rent, utilities' },
    { id: 2, name: 'Discretionary', description: 'Optional expenses like entertainment, shopping' },
    { id: 3, name: 'Investment', description: 'Money saved or invested for future' },
    { id: 4, name: 'Emergency', description: 'Unexpected or emergency expenses' }
  ];

  bankTypes: BankType[] = [
    { id: 1, name: 'Chase Bank', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
    { id: 2, name: 'Bank of America', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
    { id: 3, name: 'Wells Fargo', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
    { id: 4, name: 'Citibank', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
    { id: 5, name: 'Cash', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1' }
  ];

  cards: Card[] = [
    { id: 1, name: 'Chase Freedom', bankTypeId: 1, lastFourDigits: '1234' },
    { id: 2, name: 'Chase Sapphire', bankTypeId: 1, lastFourDigits: '5678' },
    { id: 3, name: 'BOA Cash Rewards', bankTypeId: 2, lastFourDigits: '9012' },
    { id: 4, name: 'Wells Fargo Active', bankTypeId: 3, lastFourDigits: '3456' },
    { id: 5, name: 'Citi Double Cash', bankTypeId: 4, lastFourDigits: '7890' }
  ];

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
    private themeService: ThemeService
  ) {}

  ngOnInit(): void {
    this.initializeColumnDefs();
    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
    // Don't add empty row here, wait for modal to open
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
            return new Date(params.value).toLocaleDateString();
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
         headerName: 'Category',
         field: 'categoryId',
         cellEditor: 'agSelectCellEditor',
         cellEditorParams: {
           values: this.categories.map(cat => cat.name)
         },
         valueGetter: (params) => {
           const category = this.getCategoryById(params.data.categoryId);
           return category ? category.name : '';
         },
         valueSetter: (params) => {
           const category = this.categories.find(cat => cat.name === params.newValue);
           if (category) {
             params.data.categoryId = category.id;
             return true;
           }
           return false;
         },
         cellRenderer: (params: ICellRendererParams) => {
           const category = this.getCategoryById(params.data.categoryId);
           if (category) {
             return `
               <div class="flex items-center space-x-2">
                 <svg class="w-4 h-4 ${category.color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${category.icon}"></path>
                 </svg>
                 <span>${category.name}</span>
               </div>
             `;
           }
           return '';
         },
         width: 150
       },
             {
         headerName: 'Subcategory',
         field: 'subcategoryId',
         cellEditor: 'agSelectCellEditor',
         cellEditorParams: (params: ICellEditorParams) => {
           const categoryId = params.node?.data?.categoryId;
           const subcategories = this.getSubcategoriesForCategory(categoryId);
           return subcategories.map(sub => sub.name);
         },
         valueGetter: (params) => {
           const subcategory = this.getSubcategoryById(params.data.subcategoryId);
           return subcategory ? subcategory.name : '';
         },
         valueSetter: (params) => {
           const categoryId = params.data.categoryId;
           const subcategories = this.getSubcategoriesForCategory(categoryId);
           const subcategory = subcategories.find(sub => sub.name === params.newValue);
           if (subcategory) {
             params.data.subcategoryId = subcategory.id;
             return true;
           }
           return false;
         },
         width: 130
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
         headerName: 'Budget Type',
         field: 'budgetTypeId',
         cellEditor: 'agSelectCellEditor',
         cellEditorParams: {
           values: this.budgetTypes.map(budget => budget.name)
         },
         valueGetter: (params) => {
           const budgetType = this.getBudgetTypeById(params.data.budgetTypeId);
           return budgetType ? budgetType.name : '';
         },
         valueSetter: (params) => {
           const budgetType = this.budgetTypes.find(budget => budget.name === params.newValue);
           if (budgetType) {
             params.data.budgetTypeId = budgetType.id;
             return true;
           }
           return false;
         },
         width: 120
       },
       {
         headerName: 'Bank Type',
         field: 'bankTypeId',
         cellEditor: 'agSelectCellEditor',
         cellEditorParams: {
           values: this.bankTypes.map(bank => bank.name)
         },
         valueGetter: (params) => {
           const bankType = this.getBankTypeById(params.data.bankTypeId);
           return bankType ? bankType.name : '';
         },
         valueSetter: (params) => {
           const bankType = this.bankTypes.find(bank => bank.name === params.newValue);
           if (bankType) {
             params.data.bankTypeId = bankType.id;
             // Reset card when bank type changes
             params.data.cardId = undefined;
             return true;
           }
           return false;
         },
         cellRenderer: (params: ICellRendererParams) => {
           const bankType = this.getBankTypeById(params.data.bankTypeId);
           if (bankType) {
             return `
               <div class="flex items-center space-x-2">
                 <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${bankType.icon}"></path>
                 </svg>
                 <span>${bankType.name}</span>
               </div>
             `;
           }
           return '';
         },
         width: 130
       },
       {
         headerName: 'Card',
         field: 'cardId',
         cellEditor: 'agSelectCellEditor',
         cellEditorParams: (params: ICellEditorParams) => {
           const bankTypeId = params.node?.data?.bankTypeId;
           if (bankTypeId === 5) { // Cash
             return ['Cash'];
           }
           const cards = this.getCardsForBankType(bankTypeId);
           return cards.map(card => `${card.name} (****${card.lastFourDigits})`);
         },
         valueGetter: (params) => {
           const card = this.getCardById(params.data.cardId);
           if (card) {
             return `${card.name} (****${card.lastFourDigits})`;
           }
           if (params.data.bankTypeId === 5) { // Cash
             return 'Cash';
           }
           return '';
         },
         valueSetter: (params) => {
           if (params.newValue === 'Cash') {
             params.data.cardId = undefined;
             return true;
           }
           const bankTypeId = params.data.bankTypeId;
           const cards = this.getCardsForBankType(bankTypeId);
           const card = cards.find(c => `${c.name} (****${c.lastFourDigits})` === params.newValue);
           if (card) {
             params.data.cardId = card.id;
             return true;
           }
           return false;
         },
         width: 150
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
    console.log('Adding empty row');
    const newTransaction: ManualTransaction = {
      id: this.generateId(),
      date: new Date(),
      categoryId: 0,
      amount: 0,
      description: '',
      merchant: '',
      subcategoryId: undefined,
      budgetTypeId: undefined,
      bankTypeId: undefined,
      cardId: undefined
    };
    
    this.rowData.push(newTransaction);
    console.log('Current rowData:', this.rowData);
    
    if (this.gridApi) {
      console.log('Grid API available, applying transaction');
      this.gridApi.applyTransaction({ add: [newTransaction] });
    } else {
      // If grid isn't ready yet, the data will be set when grid is ready
      console.log('Grid not ready yet, row will be added when ready');
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
    const allData: ManualTransaction[] = [];
    this.gridApi.forEachNode((node) => {
      if (node.data) {
        allData.push(node.data);
      }
    });

    // Filter out empty rows
    const validTransactions = allData.filter(transaction => 
      transaction.amount > 0 && 
      transaction.categoryId > 0 && 
      transaction.description.trim() !== '' && 
      transaction.merchant.trim() !== ''
    );

    if (validTransactions.length > 0) {
      this.transactionsSaved.emit(validTransactions);
      this.closeModal.emit();
    } else {
      alert('Please add at least one valid transaction before saving.');
    }
  }

  onCancel(): void {
    this.closeModal.emit();
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.onCancel();
    }
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  getCategoryById(id: number): Category | undefined {
    return this.categories.find(cat => cat.id === id);
  }

  getSubcategoryById(id: number): Subcategory | undefined {
    return this.subcategories.find(sub => sub.id === id);
  }

  getBudgetTypeById(id: number): BudgetType | undefined {
    return this.budgetTypes.find(budget => budget.id === id);
  }

  getSubcategoriesForCategory(categoryId: number): Subcategory[] {
    return this.subcategories.filter(sub => sub.categoryId === categoryId);
  }

  getBankTypeById(id: number): BankType | undefined {
    return this.bankTypes.find(bank => bank.id === id);
  }

  getCardById(id: number): Card | undefined {
    return this.cards.find(card => card.id === id);
  }

  getCardsForBankType(bankTypeId: number): Card[] {
    return this.cards.filter(card => card.bankTypeId === bankTypeId);
  }
}
