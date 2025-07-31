import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { BackendLoggingService } from './backend-logging.service';

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  isRead: boolean;
  createdAt: Date;
  actionUrl?: string;
  isSystem?: boolean; // New property to distinguish system notifications
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private notificationsSubject = new BehaviorSubject<Notification[]>([]);
  public notifications$ = this.notificationsSubject.asObservable();

  constructor(private backendLogging: BackendLoggingService) {
    this.loadMockNotifications();
  }

  getNotifications(): Observable<Notification[]> {
    return this.notifications$;
  }

  getUnreadCount(): Observable<number> {
    return new Observable(observer => {
      this.notifications$.subscribe(notifications => {
        // Only count user-facing notifications, not system ones
        const unreadCount = notifications.filter(n => !n.isRead && !n.isSystem).length;
        observer.next(unreadCount);
      });
    });
  }

  markAsRead(notificationId: string): void {
    const currentNotifications = this.notificationsSubject.value;
    const updatedNotifications = currentNotifications.map(notification => 
      notification.id === notificationId 
        ? { ...notification, isRead: true }
        : notification
    );
    this.notificationsSubject.next(updatedNotifications);
  }

  markAllAsRead(): void {
    const currentNotifications = this.notificationsSubject.value;
    const updatedNotifications = currentNotifications.map(notification => ({
      ...notification,
      isRead: true
    }));
    this.notificationsSubject.next(updatedNotifications);
  }

  addNotification(notification: Omit<Notification, 'id' | 'createdAt'>): void {
    const newNotification: Notification = {
      ...notification,
      id: this.generateId(),
      createdAt: new Date()
    };
    
    const currentNotifications = this.notificationsSubject.value;
    this.notificationsSubject.next([newNotification, ...currentNotifications]);
  }

  // New method for logging system errors without showing to users
  async logSystemError(title: string, message: string, error?: any): Promise<void> {
    // Log to console for debugging
    console.error(`System Error - ${title}:`, message, error);
    
    // Create a system notification that won't be shown to users
    const systemNotification: Notification = {
      id: this.generateId(),
      title,
      message,
      type: 'error',
      isRead: true, // Mark as read so it doesn't show in unread count
      createdAt: new Date(),
      isSystem: true // Mark as system notification
    };
    
    // Add to notifications but it won't be displayed in UI
    const currentNotifications = this.notificationsSubject.value;
    this.notificationsSubject.next([systemNotification, ...currentNotifications]);
    
    // Log to backend database for persistence and audit
    try {
      await this.backendLogging.logSystemError(title, message, error, 'FRONTEND', 'NOTIFICATION_SERVICE');
    } catch (backendError) {
      console.error('Failed to log system error to backend:', backendError);
    }
  }

  // Method to get system notifications for debugging (admin/dev use only)
  getSystemNotifications(): Observable<Notification[]> {
    return new Observable(observer => {
      this.notifications$.subscribe(notifications => {
        const systemNotifications = notifications.filter(n => n.isSystem);
        observer.next(systemNotifications);
      });
    });
  }

  // Method to clear system notifications (admin/dev use only)
  clearSystemNotifications(): void {
    const currentNotifications = this.notificationsSubject.value;
    const userNotifications = currentNotifications.filter(n => !n.isSystem);
    this.notificationsSubject.next(userNotifications);
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  private loadMockNotifications(): void {
    const mockNotifications: Notification[] = [
      {
        id: '1',
        title: 'Welcome to Spendlyzer!',
        message: 'Your account has been successfully created. Start tracking your expenses now.',
        type: 'success',
        isRead: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
        actionUrl: '/dashboard'
      },
      {
        id: '2',
        title: 'New Transaction Detected',
        message: 'A new transaction of $45.67 has been added to your account.',
        type: 'info',
        isRead: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
        actionUrl: '/transactions'
      },
      {
        id: '3',
        title: 'Monthly Report Ready',
        message: 'Your monthly spending report for January is now available.',
        type: 'info',
        isRead: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
        actionUrl: '/reports'
      },
      {
        id: '4',
        title: 'Budget Alert',
        message: 'You\'ve reached 80% of your dining budget for this month.',
        type: 'warning',
        isRead: false,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2), // 2 days ago
        actionUrl: '/budget'
      },
      {
        id: '5',
        title: 'Family Invitation Sent',
        message: 'Invitation sent to john.doe@example.com for family group access.',
        type: 'success',
        isRead: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3), // 3 days ago
        actionUrl: '/family'
      },
      {
        id: '6',
        title: 'Account Connected',
        message: 'Your Chase Bank account has been successfully connected.',
        type: 'success',
        isRead: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 4), // 4 days ago
        actionUrl: '/accounts'
      },
      {
        id: '7',
        title: 'Security Update',
        message: 'Your password was changed successfully from a new device.',
        type: 'info',
        isRead: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5), // 5 days ago
        actionUrl: '/security'
      },
      {
        id: '8',
        title: 'Feature Available',
        message: 'New expense categorization feature is now available in your dashboard.',
        type: 'info',
        isRead: true,
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 6), // 6 days ago
        actionUrl: '/features'
      }
    ];
    
    this.notificationsSubject.next(mockNotifications);
  }
} 