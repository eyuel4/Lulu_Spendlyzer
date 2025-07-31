import { Component, OnInit, HostListener } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ThemeService, Theme } from '../../services/theme.service';
import { NotificationService, Notification } from '../../services/notification.service';
import { ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

interface User {
  first_name?: string;
  last_name?: string;
  email?: string;
  family_group?: {
    name: string;
  };
}

interface Transaction {
  description: string;
  category: string;
  amount: number;
  date: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
  imports: [ReactiveFormsModule, CommonModule]
})
export class DashboardComponent implements OnInit {
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

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private themeService: ThemeService,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    // Check for token in URL (from Google OAuth redirect)
    this.handleOAuthToken();
    
    this.loadUserData();
    this.loadMockTransactions();
    this.loadNotifications();
    
    // Subscribe to theme changes
    this.themeService.currentTheme$.subscribe(theme => {
      this.currentTheme = theme;
    });
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

  private loadMockTransactions(): void {
    // Mock data for demonstration
    this.recentTransactions = [
      {
        description: 'Grocery Store',
        category: 'Food & Dining',
        amount: 85.50,
        date: '2024-01-15'
      },
      {
        description: 'Gas Station',
        category: 'Transportation',
        amount: 45.00,
        date: '2024-01-14'
      },
      {
        description: 'Netflix Subscription',
        category: 'Entertainment',
        amount: 15.99,
        date: '2024-01-13'
      },
      {
        description: 'Coffee Shop',
        category: 'Food & Dining',
        amount: 4.50,
        date: '2024-01-12'
      }
    ];
  }
} 