import { Component, OnInit, HostListener, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
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
import { ManualTransactionModalComponent, ManualTransaction } from '../manual-transaction-modal/manual-transaction-modal.component';

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
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AgGridAngular, ExpenseBreakdownComponent, AddTransactionModalComponent, ManualTransactionModalComponent]
})
export class DashboardComponent implements OnInit, AfterViewInit {
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
    { field: 'date', headerName: 'Date', sortable: true, filter: true, width: 120 },
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
    domLayout: 'autoHeight',
    animateRows: true,
    rowSelection: 'single'
  };

  categoryData: CategoryData[] = [];

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private themeService: ThemeService,
    private notificationService: NotificationService,
    private userPreferencesService: UserPreferencesService
  ) {}

  ngOnInit(): void {
    // Check for token in URL (from Google OAuth redirect)
    this.handleOAuthToken();
    
    this.initializeDatePicker();
    this.loadUserData();
    this.loadDashboardData();
    this.loadNotifications();
    
    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
  }

  ngAfterViewInit(): void {
    // Component initialization
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
    this.gridApi.sizeColumnsToFit();
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
    // Mock data based on selected month and year
    const mockData = this.getMockDataForMonthYear(this.selectedMonth, this.selectedYear);
    this.dashboardData = mockData;
    this.rowData = mockData.transactions;
    this.categoryData = mockData.categoryData;
    
    // Component data loaded
  }

  private getMockDataForMonthYear(month: number, year: number): any {
    const baseTransactions = [
      {
        id: 1,
        description: 'Grocery Store',
        category: 'Food & Dining',
        amount: 85.50,
        date: '2024-01-15',
        type: 'expense' as const,
        merchant: 'Walmart'
      },
      {
        id: 2,
        description: 'Gas Station',
        category: 'Transportation',
        amount: 45.00,
        date: '2024-01-14',
        type: 'expense' as const,
        merchant: 'Shell'
      },
      {
        id: 3,
        description: 'Netflix Subscription',
        category: 'Entertainment',
        amount: 15.99,
        date: '2024-01-13',
        type: 'expense' as const,
        merchant: 'Netflix'
      },
      {
        id: 4,
        description: 'Coffee Shop',
        category: 'Food & Dining',
        amount: 4.50,
        date: '2024-01-12',
        type: 'expense' as const,
        merchant: 'Starbucks'
      },
      {
        id: 5,
        description: 'Rent Payment',
        category: 'Housing',
        amount: 1200.00,
        date: '2024-01-01',
        type: 'expense' as const,
        merchant: 'Property Management'
      },
      {
        id: 6,
        description: 'Electric Bill',
        category: 'Utilities',
        amount: 89.50,
        date: '2024-01-10',
        type: 'expense' as const,
        merchant: 'Power Company'
      },
      {
        id: 7,
        description: 'Salary',
        category: 'Income',
        amount: 5000.00,
        date: '2024-01-01',
        type: 'income' as const,
        merchant: 'Company Inc'
      }
    ];

    // Generate mock data based on month and year
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December'];
    
    // Simulate different spending patterns based on month
    let totalSpending = 2847.32;
    let savings = 1152.68;
    let transactionCount = 47;
    
    // Adjust spending based on month (holiday season, etc.)
    if (month === 12) { // December - holiday spending
      totalSpending = 4200.00;
      savings = 800.00;
      transactionCount = 65;
    } else if (month === 7 || month === 8) { // Summer months
      totalSpending = 3200.00;
      savings = 1800.00;
      transactionCount = 55;
    } else if (month === 1) { // January - post-holiday
      totalSpending = 2200.00;
      savings = 2800.00;
      transactionCount = 40;
    }
    
    // Adjust for year (inflation, etc.)
    const yearDiff = year - 2024;
    if (yearDiff > 0) {
      totalSpending *= (1 + yearDiff * 0.05); // 5% increase per year
      savings *= (1 + yearDiff * 0.03); // 3% increase per year
    } else if (yearDiff < 0) {
      totalSpending *= (1 + yearDiff * 0.05); // 5% decrease per year
      savings *= (1 + yearDiff * 0.03); // 3% decrease per year
    }
    
    return {
      totalSpending: Math.round(totalSpending * 100) / 100,
      monthlyBudget: 4000,
      savings: Math.round(savings * 100) / 100,
      transactionCount: transactionCount,
      transactions: baseTransactions,
      categoryData: this.generateCategoryData(baseTransactions),
      periodName: `${monthNames[month - 1]} ${year}`
    };
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

  onManualTransactionsSaved(transactions: ManualTransaction[]): void {
    console.log('Manual transactions saved:', transactions);
    // TODO: Save transactions to backend
    // For now, just close the modal
    this.showManualTransactionModal = false;
    
    // Optionally refresh the dashboard data
    this.loadDashboardData();
  }


} 