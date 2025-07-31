import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface SystemLogEntry {
  title: string;
  message: string;
  error_type?: string;
  error_details?: string;
  category: string;
  source: string;
  user_id?: number;
  session_id?: string;
  request_id?: string;
  endpoint?: string;
  method?: string;
  ip_address?: string;
  user_agent?: string;
  meta?: any;
  tags?: string[];
}

export interface AuditLogEntry {
  event_type: string;
  resource_type: string;
  resource_id?: string;
  user_id?: number;
  performed_by?: number;
  action: string;
  details?: string;
  changes?: any;
  is_successful: string;
  failure_reason?: string;
  ip_address?: string;
  user_agent?: string;
  session_id?: string;
  request_id?: string;
  meta?: any;
}

@Injectable({
  providedIn: 'root'
})
export class BackendLoggingService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Log a system error to the backend
   */
  async logSystemError(
    title: string,
    message: string,
    error?: any,
    category: string = 'FRONTEND',
    source: string = 'ANGULAR',
    metadata?: any
  ): Promise<void> {
    try {
      const logEntry: SystemLogEntry = {
        title,
        message,
        error_type: error?.name || error?.constructor?.name,
        error_details: error?.message || error?.stack || JSON.stringify(error),
        category,
        source,
        meta: metadata || {},
        tags: ['frontend', 'error'],
        user_agent: navigator.userAgent,
        // Add user context if available
        user_id: this.getCurrentUserId(),
        session_id: this.getSessionId(),
        request_id: this.generateRequestId()
      };

      // Send to backend logging service
      await this.http.post(`${this.apiUrl}/logs/system`, logEntry).toPromise();
    } catch (loggingError) {
      // If backend logging fails, fall back to console
      console.error('Failed to log to backend:', loggingError);
      console.error('Original error:', { title, message, error });
    }
  }

  /**
   * Log a system warning to the backend
   */
  async logSystemWarning(
    title: string,
    message: string,
    category: string = 'FRONTEND',
    source: string = 'ANGULAR',
    metadata?: any
  ): Promise<void> {
    try {
      const logEntry: SystemLogEntry = {
        title,
        message,
        category,
        source,
        meta: metadata || {},
        tags: ['frontend', 'warning'],
        user_agent: navigator.userAgent,
        user_id: this.getCurrentUserId(),
        session_id: this.getSessionId(),
        request_id: this.generateRequestId()
      };

      await this.http.post(`${this.apiUrl}/logs/system`, logEntry).toPromise();
    } catch (loggingError) {
      console.warn('Failed to log warning to backend:', loggingError);
      console.warn('Original warning:', { title, message });
    }
  }

  /**
   * Log an audit event to the backend
   */
  async logAuditEvent(
    event_type: string,
    resource_type: string,
    action: string,
    details?: string,
    changes?: any,
    is_successful: string = 'SUCCESS',
    failure_reason?: string,
    metadata?: any
  ): Promise<void> {
    try {
      const auditEntry: AuditLogEntry = {
        event_type,
        resource_type,
        action,
        details,
        changes,
        is_successful,
        failure_reason,
        user_id: this.getCurrentUserId(),
        performed_by: this.getCurrentUserId(),
        ip_address: await this.getClientIP(),
        user_agent: navigator.userAgent,
        session_id: this.getSessionId(),
        request_id: this.generateRequestId(),
        meta: metadata || {}
      };

      await this.http.post(`${this.apiUrl}/logs/audit`, auditEntry).toPromise();
    } catch (loggingError) {
      console.error('Failed to log audit event to backend:', loggingError);
      console.log('Audit event:', { event_type, resource_type, action, details });
    }
  }

  /**
   * Get current user ID from localStorage or session
   */
  private getCurrentUserId(): number | undefined {
    try {
      let userStr: string | null = null;
      if (typeof window !== 'undefined' && window.localStorage) {
        userStr = localStorage.getItem('currentUser');
      }
      if (userStr) {
        const user = JSON.parse(userStr);
        return user.id;
      }
    } catch (error) {
      console.warn('Failed to get current user ID:', error);
    }
    return undefined;
  }

  /**
   * Get session ID from localStorage or generate one
   */
  private getSessionId(): string {
    let sessionId: string | null = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      sessionId = localStorage.getItem('sessionId');
    }
    if (!sessionId) {
      sessionId = this.generateSessionId();
    }
    if (typeof window !== 'undefined' && window.localStorage && sessionId) {
      localStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  /**
   * Generate a unique session ID
   */
  private generateSessionId(): string {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Generate a unique request ID
   */
  private generateRequestId(): string {
    return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Get client IP address (this is a simplified version)
   * In a real application, you might get this from your backend
   */
  private async getClientIP(): Promise<string | undefined> {
    try {
      // This is a simplified approach - in production you'd get this from your backend
      const response = await fetch('https://api.ipify.org?format=json');
      const data = await response.json();
      return data.ip;
    } catch (error) {
      console.warn('Failed to get client IP:', error);
      return undefined;
    }
  }
} 