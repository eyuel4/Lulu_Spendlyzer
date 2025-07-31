import { Injectable } from '@angular/core';

export interface CacheItem<T> {
  value: T;
  timestamp: number;
  ttl: number; // Time to live in milliseconds
}

@Injectable({
  providedIn: 'root'
})
export class CacheService {
  private readonly CACHE_PREFIX = 'spendlyzer_cache_';
  private readonly SESSION_PREFIX = 'spendlyzer_session_';

  constructor() {}

  // Local Storage Cache (persistent)
  setLocal<T>(key: string, value: T, ttlMinutes: number = 60): void {
    try {
      const cacheItem: CacheItem<T> = {
        value,
        timestamp: Date.now(),
        ttl: ttlMinutes * 60 * 1000
      };
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(this.CACHE_PREFIX + key, JSON.stringify(cacheItem));
      }
    } catch (error) {
      console.warn('Failed to set local cache:', error);
    }
  }

  getLocal<T>(key: string): T | null {
    try {
      let item: string | null = null;
      if (typeof window !== 'undefined' && window.localStorage) {
        item = localStorage.getItem(this.CACHE_PREFIX + key);
      }
      if (!item) return null;

      const cacheItem: CacheItem<T> = JSON.parse(item);
      const isExpired = Date.now() - cacheItem.timestamp > cacheItem.ttl;

      if (isExpired) {
        this.removeLocal(key);
        return null;
      }

      return cacheItem.value;
    } catch (error) {
      console.warn('Failed to get local cache:', error);
      return null;
    }
  }

  removeLocal(key: string): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.removeItem(this.CACHE_PREFIX + key);
      }
    } catch (error) {
      console.warn('Failed to remove local cache:', error);
    }
  }

  clearLocal(): void {
    try {
      let keys: string[] = [];
      if (typeof window !== 'undefined' && window.localStorage) {
        keys = Object.keys(localStorage);
      }
      keys.forEach(key => {
        if (key.startsWith(this.CACHE_PREFIX)) {
          if (typeof window !== 'undefined' && window.localStorage) {
            localStorage.removeItem(key);
          }
        }
      });
    } catch (error) {
      console.warn('Failed to clear local cache:', error);
    }
  }

  // Session Storage Cache (temporary)
  setSession<T>(key: string, value: T, ttlMinutes: number = 30): void {
    try {
      const cacheItem: CacheItem<T> = {
        value,
        timestamp: Date.now(),
        ttl: ttlMinutes * 60 * 1000
      };
      if (typeof window !== 'undefined' && window.sessionStorage) {
        sessionStorage.setItem(this.SESSION_PREFIX + key, JSON.stringify(cacheItem));
      }
    } catch (error) {
      console.warn('Failed to set session cache:', error);
    }
  }

  getSession<T>(key: string): T | null {
    try {
      let item: string | null = null;
      if (typeof window !== 'undefined' && window.sessionStorage) {
        item = sessionStorage.getItem(this.SESSION_PREFIX + key);
      }
      if (!item) return null;

      const cacheItem: CacheItem<T> = JSON.parse(item);
      const isExpired = Date.now() - cacheItem.timestamp > cacheItem.ttl;

      if (isExpired) {
        this.removeSession(key);
        return null;
      }

      return cacheItem.value;
    } catch (error) {
      console.warn('Failed to get session cache:', error);
      return null;
    }
  }

  removeSession(key: string): void {
    try {
      if (typeof window !== 'undefined' && window.sessionStorage) {
        sessionStorage.removeItem(this.SESSION_PREFIX + key);
      }
    } catch (error) {
      console.warn('Failed to remove session cache:', error);
    }
  }

  clearSession(): void {
    try {
      let keys: string[] = [];
      if (typeof window !== 'undefined' && window.sessionStorage) {
        keys = Object.keys(sessionStorage);
      }
      keys.forEach(key => {
        if (key.startsWith(this.SESSION_PREFIX)) {
          if (typeof window !== 'undefined' && window.sessionStorage) {
            sessionStorage.removeItem(key);
          }
        }
      });
    } catch (error) {
      console.warn('Failed to clear session cache:', error);
    }
  }

  // Cache key generators
  static keys = {
    user: (userId: number) => `user_${userId}`,
    userPreferences: (userId: number) => `user_preferences_${userId}`,
    transactions: (userId: number, month?: string) => 
      month ? `transactions_${userId}_${month}` : `transactions_${userId}`,
    categories: (userId: number) => `categories_${userId}`,
    reports: (userId: number, reportType: string, month?: string) =>
      month ? `reports_${userId}_${reportType}_${month}` : `reports_${userId}_${reportType}`,
    familyGroup: (familyId: number) => `family_group_${familyId}`,
    familyMembers: (familyId: number) => `family_members_${familyId}`
  };

  // Utility methods
  isExpired(timestamp: number, ttlMinutes: number): boolean {
    return Date.now() - timestamp > ttlMinutes * 60 * 1000;
  }

  getCacheStats(): { local: number; session: number } {
    try {
      let localKeys: string[] = [];
      if (typeof window !== 'undefined' && window.localStorage) {
        localKeys = Object.keys(localStorage).filter(key => 
          key.startsWith(this.CACHE_PREFIX)
        );
      }
      
      let sessionKeys: string[] = [];
      if (typeof window !== 'undefined' && window.sessionStorage) {
        sessionKeys = Object.keys(sessionStorage).filter(key => 
          key.startsWith(this.SESSION_PREFIX)
        );
      }

      return { local: localKeys.length, session: sessionKeys.length };
    } catch (error) {
      return { local: 0, session: 0 };
    }
  }
} 