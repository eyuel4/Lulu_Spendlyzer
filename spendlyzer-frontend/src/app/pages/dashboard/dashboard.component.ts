import { Component, OnInit, OnDestroy, HostListener, ViewChild, ElementRef, AfterViewInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ThemeService, Theme } from '../../services/theme.service';
import { NotificationService, Notification } from '../../services/notification.service';
import { UserPreferencesService } from '../../services/user-preferences.service';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridReadyEvent, GridApi, GridOptions } from 'ag-grid-community';
import { ExpenseBreakdownComponent, CategoryData } from '../expense-breakdown/expense-breakdown.component';
import { AddTransactionModalComponent } from '../add-transaction-modal/add-transaction-modal.component';
import { ManualTransactionModalComponent } from '../manual-transaction-modal/manual-transaction-modal.component';
import { BankConnectionModalComponent } from '../bank-connection-modal/bank-connection-modal.component';
import { PlaidService, PlaidAccount } from '../../services/plaid.service';
import { TransactionService, Transaction as ApiTransaction } from '../../services/transaction.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

interface User {
  first_name?: string;
  last_name?: string;
  email?: string;
  family_group?: {
    name: string;
  };
}

interface Transaction {
  id: number;
  description: string;
  category: string;
  amount: number;
  date: string;
  type: 'expense' | 'income';
  merchant: string;
}



@Component({
  selector: 'app-dashboard',
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AgGridAngular, ExpenseBreakdownComponent, AddTransactionModalComponent, ManualTransactionModalComponent, BankConnectionModalComponent]
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  user: User | null = null;
  recentTransactions: Transaction[] = [];
  loading = true;
  error: string | null = null;
  currentTheme: Theme = 'light';
  showMobileMenu = false;
  showUserDropdown = false;
  showNotificationDropdown = false;
  notifications: Notification[] = [];
  unreadCount = 0;
  selectedDateRange = 'current-month';
  selectedMonth = new Date().getMonth() + 1; // Current month (1-12)
  selectedYear = new Date().getFullYear(); // Current year
  selectedPreset = '';
  availableYears: number[] = [];
  showAddTransactionModal = false;
  showManualTransactionModal = false;
  dashboardData: any = null;
  dataLoading = false;
  
  // AgGrid properties
  @ViewChild(AgGridAngular) agGrid!: AgGridAngular;
  gridApi!: GridApi;
  rowData: Transaction[] = [];
  columnDefs: ColDef[] = [
    { 
      field: 'date', 
      headerName: 'Date', 
      sortable: true, 
      filter: true, 
      width: 120,
      valueFormatter: (params: any) => {
        if (!params.value) return '';
        return new Date(params.value).toLocaleDateString();
      }
    },
    { field: 'merchant', headerName: 'Merchant', sortable: true, filter: true, width: 200 },
    { field: 'description', headerName: 'Description', sortable: true, filter: true, width: 250 },
    { field: 'category', headerName: 'Category', sortable: true, filter: true, width: 150 },
    { 
      field: 'amount', 
      headerName: 'Amount', 
      sortable: true, 
      filter: true, 
      width: 120,
      cellRenderer: (params: any) => {
        const isExpense = params.data.type === 'expense';
        const color = isExpense ? 'text-red-600' : 'text-green-600';
        const prefix = isExpense ? '-' : '+';
        return `<span class="${color} font-semibold">${prefix}$${Math.abs(params.value).toFixed(2)}</span>`;
      }
    }
  ];
  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true
  };

  // AG Grid v33+ theme configuration
  gridOptions: GridOptions = {
    domLayout: 'normal',
    animateRows: true,
    rowSelection: 'single',
    suppressHorizontalScroll: false
  };

  categoryData: CategoryData[] = [];
  
  // Plaid integration
  showBankConnectionModal = false;
  connectedBanksCount = 0;
  connectedBanks: PlaidAccount[] = [];

  private destroy$ = new Subject<void>();

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private themeService: ThemeService,
    private notificationService: NotificationService,
    private userPreferencesService: UserPreferencesService,
    private plaidService: PlaidService,
    private transactionService: TransactionService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    // Check for token in URL (from Google OAuth redirect)
    this.handleOAuthToken();
    
    this.initializeDatePicker();
    this.loadUserData();
    this.loadDashboardData();
    this.loadNotifications();
    
    // Only load connected banks in browser (avoid SSR issues)
    if (isPlatformBrowser(this.platformId)) {
      this.loadConnectedBanks();
    }
    
    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
  }

  ngAfterViewInit(): void {
    // Component initialization
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/signin']);
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  toggleMobileMenu(): void {
    this.showMobileMenu = !this.showMobileMenu;
  }

  toggleUserDropdown(): void {
    this.showUserDropdown = !this.showUserDropdown;
    if (this.showUserDropdown) {
      this.showNotificationDropdown = false;
    }
  }

  toggleNotificationDropdown(): void {
    this.showNotificationDropdown = !this.showNotificationDropdown;
    if (this.showNotificationDropdown) {
      this.showUserDropdown = false;
    }
  }

  closeDropdowns(): void {
    this.showUserDropdown = false;
    this.showNotificationDropdown = false;
  }

  onUserMenuClick(event: Event): void {
    event.stopPropagation();
    this.toggleUserDropdown();
  }

  onNotificationClick(event: Event): void {
    event.stopPropagation();
    this.toggleNotificationDropdown();
  }

  markNotificationAsRead(notificationId: string): void {
    this.notificationService.markAsRead(notificationId);
  }

  markAllNotificationsAsRead(): void {
    this.notificationService.markAllAsRead();
  }

  onNotificationItemClick(notification: Notification): void {
    this.markNotificationAsRead(notification.id);
    if (notification.actionUrl) {
      this.router.navigate([notification.actionUrl]);
    }
    this.closeDropdowns();
  }

  onUserMenuItemClick(action: string): void {
    this.closeDropdowns();
    switch (action) {
      case 'profile':
        this.router.navigate(['/profile']);
        break;
      case 'account':
        this.router.navigate(['/account']);
        break;
      case 'billing':
        this.router.navigate(['/billing']);
        break;
      case 'help':
        this.router.navigate(['/help']);
        break;
      case 'tour':
        this.router.navigate(['/tour']);
        break;
      case 'feature':
        this.router.navigate(['/request-feature']);
        break;
      case 'logout':
        this.logout();
        break;
    }
  }

  loadUserData(): void {
    this.loading = true;
    this.error = null;
    
    this.authService.fetchCurrentUser().subscribe({
      next: (userData) => {
        console.log('User data loaded:', userData);
        this.user = {
          first_name: userData.first_name,
          last_name: userData.last_name,
          email: userData.email,
          family_group: userData.family_group || { name: 'My Family' }
        };
        this.loading = false;
        
        // Check if user has preferences (first-time user check)
        this.checkUserPreferences();
      },
      error: (error) => {
        console.error('Error loading user data:', error);
        this.error = 'Failed to load user data';
        this.loading = false;
        
        // If there's an authentication error, redirect to signin
        if (error.status === 401) {
          this.router.navigate(['/signin']);
        }
      }
    });
  }

  private checkUserPreferences(): void {
    this.authService.getUserPreferences().subscribe({
      next: (preferences) => {
        console.log('User preferences:', preferences);
        
        // If user doesn't have preferences, redirect to questionnaire
        if (!preferences.has_preferences) {
          console.log('First-time user detected, redirecting to questionnaire');
          this.router.navigate(['/questionnaire']);
        }
      },
      error: (error) => {
        console.error('Error checking user preferences:', error);
        // If there's an error checking preferences, assume first-time user
        console.log('Error checking preferences, redirecting to questionnaire');
        this.router.navigate(['/questionnaire']);
      }
    });
  }

  private handleOAuthToken(): void {
    // Get token from URL query parameters
    this.route.queryParamMap.subscribe(params => {
      const token = params.get('token');
      if (token) {
        console.log('OAuth token received, storing in localStorage');
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem('access_token', token);
        }
        
        // Clear the token from URL
        this.router.navigate(['/dashboard'], { 
          queryParams: {}, 
          replaceUrl: true 
        });
        
        // Refresh user data with new token
        this.loadUserData();
      }
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    // Close dropdowns when clicking outside
    const target = event.target as HTMLElement;
    if (!target.closest('.user-dropdown') && !target.closest('.notification-dropdown')) {
      this.closeDropdowns();
    }
  }

  private loadNotifications(): void {
    this.notificationService.getNotifications().subscribe(notifications => {
      // Filter out system notifications from the UI
      this.notifications = notifications.filter(notification => !notification.isSystem);
    });

    this.notificationService.getUnreadCount().subscribe(count => {
      this.unreadCount = count;
    });
  }



  onGridReady(params: GridReadyEvent): void {
    this.gridApi = params.api;
    // Auto-size columns to fit container
    setTimeout(() => {
      if (this.gridApi) {
        this.gridApi.sizeColumnsToFit();
      }
    }, 100);
  }

  getCategoryIcon(category: string): string {
    const iconMap: { [key: string]: string } = {
      'Food & Dining': '🍽️',
      'Transportation': '🚗',
      'Housing': '🏠',
      'Entertainment': '🎬',
      'Shopping': '🛍️',
      'Healthcare': '🏥',
      'Utilities': '⚡',
      'Travel': '✈️',
      'Education': '📚',
      'Insurance': '🛡️',
      'Gifts': '🎁',
      'Personal Care': '💄',
      'Pets': '🐕',
      'Subscriptions': '📱',
      'Other': '📦'
    };
    return iconMap[category] || '📦';
  }

  getCategoryColor(category: string): string {
    const colorMap: { [key: string]: string } = {
      'Food & Dining': '#EF4444',
      'Transportation': '#3B82F6',
      'Housing': '#10B981',
      'Entertainment': '#8B5CF6',
      'Shopping': '#F59E0B',
      'Healthcare': '#EC4899',
      'Utilities': '#06B6D4',
      'Travel': '#84CC16',
      'Education': '#6366F1',
      'Insurance': '#F97316',
      'Gifts': '#A855F7',
      'Personal Care': '#14B8A6',
      'Pets': '#F43F5E',
      'Subscriptions': '#0EA5E9',
      'Other': '#6B7280'
    };
    return colorMap[category] || '#6B7280';
  }

  getBudgetPercentage(): number {
    if (!this.dashboardData) return 0;
    return Math.round((this.dashboardData.totalSpending / this.dashboardData.monthlyBudget) * 100);
  }

  initializeDatePicker(): void {
    const currentYear = new Date().getFullYear();
    // Generate years from 2020 to current year + 2 (for future planning)
    this.availableYears = Array.from({length: currentYear - 2019 + 2}, (_, i) => 2020 + i);
    
    // Set current month and year
    this.selectedMonth = new Date().getMonth() + 1;
    this.selectedYear = currentYear;
  }

  getDateRangeDisplayName(): string {
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    return `${monthNames[this.selectedMonth - 1]} ${this.selectedYear}`;
  }

  onDateRangeChange(): void {
    this.selectedPreset = ''; // Clear preset when manually selecting
    this.loadDashboardData();
  }

  onPresetChange(): void {
    if (!this.selectedPreset) return;
    
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    switch (this.selectedPreset) {
      case 'current-month':
        this.selectedMonth = currentMonth;
        this.selectedYear = currentYear;
        break;
      case 'last-month':
        if (currentMonth === 1) {
          this.selectedMonth = 12;
          this.selectedYear = currentYear - 1;
        } else {
          this.selectedMonth = currentMonth - 1;
          this.selectedYear = currentYear;
        }
        break;
      case 'current-year':
        this.selectedMonth = 1; // January
        this.selectedYear = currentYear;
        break;
      case 'last-year':
        this.selectedMonth = 1; // January
        this.selectedYear = currentYear - 1;
        break;
    }
    
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.dataLoading = true;
    
    // Build month_id from selected month and year
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    const monthId = `${monthNames[this.selectedMonth - 1]}_${this.selectedYear}`;
    
    // Fetch transactions from API
    this.transactionService.getTransactions({
      skip: 0,
      limit: 10, // Show recent 10 transactions on dashboard
      month: monthId
    }).pipe(takeUntil(this.destroy$))
    .subscribe({
      next: (transactions: ApiTransaction[]) => {
        // Transform API transactions to dashboard format
        const transformedTransactions = this.transformTransactions(transactions);
        this.rowData = transformedTransactions;
        
        // Generate category data from transactions
        this.categoryData = this.generateCategoryData(transformedTransactions);
        
        // Update dashboard data
        const totalSpending = transformedTransactions
          .filter(t => t.type === 'expense')
          .reduce((sum, t) => sum + Math.abs(t.amount), 0);
        
        this.dashboardData = {
          totalSpending: totalSpending,
          monthlyBudget: 4000, // TODO: Get from user preferences
          savings: 4000 - totalSpending,
          transactionCount: transactions.length,
          transactions: transformedTransactions,
          categoryData: this.categoryData,
          periodName: `${monthNames[this.selectedMonth - 1]} ${this.selectedYear}`
        };
        
        this.dataLoading = false;
      },
      error: (error) => {
        console.error('Error loading transactions:', error);
        this.error = 'Failed to load transactions';
        this.rowData = [];
        this.categoryData = [];
        this.dashboardData = {
          totalSpending: 0,
          monthlyBudget: 4000,
          savings: 4000,
          transactionCount: 0,
          transactions: [],
          categoryData: [],
          periodName: `${monthNames[this.selectedMonth - 1]} ${this.selectedYear}`
        };
        this.dataLoading = false;
      }
    });
  }

  private transformTransactions(apiTransactions: ApiTransaction[]): Transaction[] {
    return apiTransactions.map(t => ({
      id: t.id,
      description: t.name || 'Transaction',
      category: t.expense_category_name || t.custom_category || t.plaid_category || 'Uncategorized',
      amount: Math.abs(t.amount),
      date: t.date,
      type: t.amount < 0 ? 'expense' : 'income',
      merchant: t.merchant_name || t.name || 'Unknown'
    }));
  }


  private generateCategoryData(transactions: Transaction[]): CategoryData[] {
    const categoryMap = new Map<string, number>();
    
    // Only include expenses, not income
    transactions
      .filter(t => t.type === 'expense')
      .forEach(transaction => {
        const current = categoryMap.get(transaction.category) || 0;
        categoryMap.set(transaction.category, current + transaction.amount);
      });

    const total = Array.from(categoryMap.values()).reduce((sum, amount) => sum + amount, 0);
    
    return Array.from(categoryMap.entries()).map(([category, amount]) => ({
      category,
      amount,
      percentage: (amount / total) * 100,
      icon: this.getCategoryIcon(category),
      color: this.getCategoryColor(category)
    })).sort((a, b) => b.amount - a.amount);
  }

  onAddTransactionClick(): void {
    this.showAddTransactionModal = true;
  }

  onCloseAddTransactionModal(): void {
    this.showAddTransactionModal = false;
  }

  viewAllTransactions(): void {
    this.router.navigate(['/transactions']);
  }

  onTransactionOptionSelected(data: {option: string, setAsDefault: boolean}): void {
    console.log('Selected option:', data.option, 'Set as default:', data.setAsDefault);
    
    // Here you would typically:
    // 1. Save the default preference to the database if setAsDefault is true
    // 2. Navigate to the appropriate page or open the appropriate modal based on the option
    
    if (data.setAsDefault) {
      this.saveDefaultTransactionOption(data.option);
    }
    
    // Handle the selected option
    switch (data.option) {
      case 'bank-api':
        this.handleBankApiConnection();
        break;
      case 'upload-statement':
        this.handleUploadStatement();
        break;
      case 'manual':
        this.handleManualTransaction();
        break;
    }
  }

  private saveDefaultTransactionOption(option: string): void {
    this.userPreferencesService.updateDefaultTransactionMethod(option).subscribe({
      next: (preferences) => {
        console.log('Default transaction method saved:', preferences.defaultTransactionMethod);
        // You could show a success notification here
      },
      error: (error) => {
        console.error('Error saving default transaction method:', error);
        // You could show an error notification here
      }
    });
  }

  private handleBankApiConnection(): void {
    // TODO: Implement bank API connection flow
    console.log('Opening bank API connection flow');
    // Navigate to bank connection page or open bank selection modal
  }

  private handleUploadStatement(): void {
    // TODO: Implement file upload flow
    console.log('Opening file upload flow');
    // Open file upload modal or navigate to upload page
  }

  private handleManualTransaction(): void {
    this.showManualTransactionModal = true;
  }

  onCloseManualTransactionModal(): void {
    this.showManualTransactionModal = false;
  }

  onManualTransactionsSaved(transactions: any[]): void {
    console.log('Manual transactions saved:', transactions);
    this.showManualTransactionModal = false;
    
    // Refresh the dashboard data to show new transactions
    this.loadDashboardData();
  }

  // Plaid integration methods
  loadConnectedBanks(): void {
    this.plaidService.getConnectedAccounts().subscribe({
      next: (accounts) => {
        this.connectedBanks = accounts;
        this.connectedBanksCount = accounts.length;
      },
      error: (err) => {
        console.error('Error loading connected banks:', err);
      }
    });
  }

  openBankConnectionModal(): void {
    this.showBankConnectionModal = true;
  }

  closeBankConnectionModal(): void {
    this.showBankConnectionModal = false;
  }

  handleBankConnectionSuccess(result: any): void {
    console.log('Bank connected successfully:', result);
    this.showBankConnectionModal = false;
    this.loadConnectedBanks();
    this.loadDashboardData(); // Refresh dashboard with new transactions
  }

  navigateToConnectedBanks(): void {
    this.router.navigate(['/manage-banks']);
  }

} 