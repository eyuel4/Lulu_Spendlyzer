import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, of, BehaviorSubject } from 'rxjs';
import { tap, catchError, shareReplay } from 'rxjs/operators';
import { CacheService } from './cache.service';
import { AuthService } from './auth.service';

export interface TransactionSummary {
  total_transactions: number;
  total_amount: number;
  average_amount: number;
  min_amount: number;
  max_amount: number;
  month?: string;
}

export interface CategoryData {
  [category: string]: {
    count: number;
    total_amount: number;
  };
}

export interface DashboardData {
  summary: TransactionSummary;
  categories: CategoryData;
  recent_transactions: any[];
  family_members?: any[];
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private apiUrl = 'http://localhost:8000';
  private dashboardDataSubject = new BehaviorSubject<DashboardData | null>(null);
  public dashboardData$ = this.dashboardDataSubject.asObservable();

  constructor(
    private http: HttpClient,
    private cacheService: CacheService,
    private authService: AuthService
  ) {}

  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken();
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  private createParams(month?: string): HttpParams {
    let params = new HttpParams();
    if (month) {
      params = params.set('month', month);
    }
    return params;
  }

  getDashboardData(month?: string): Observable<DashboardData> {
    const cacheKey = month ? `dashboard_${month}` : 'dashboard';
    
    // Try to get from cache first
    const cachedData = this.cacheService.getLocal<DashboardData>(cacheKey);
    if (cachedData) {
      console.log('Dashboard data loaded from cache');
      this.dashboardDataSubject.next(cachedData);
      return of(cachedData);
    }

    // Fetch from API
    const params = this.createParams(month);
    return this.http.get<DashboardData>(`${this.apiUrl}/dashboard`, {
      headers: this.getHeaders(),
      params
    }).pipe(
      tap(data => {
        // Cache the data for 10 minutes
        this.cacheService.setLocal(cacheKey, data, 10);
        this.dashboardDataSubject.next(data);
        console.log('Dashboard data cached');
      }),
      catchError(error => {
        console.error('Error fetching dashboard data:', error);
        const fallbackData: DashboardData = {
          summary: {
            total_transactions: 0,
            total_amount: 0,
            average_amount: 0,
            min_amount: 0,
            max_amount: 0
          },
          categories: {},
          recent_transactions: []
        };
        return of(fallbackData);
      }),
      shareReplay(1)
    );
  }

  getTransactionSummary(month?: string): Observable<TransactionSummary> {
    const cacheKey = month ? `transaction_summary_${month}` : 'transaction_summary';
    
    // Try to get from cache first
    const cachedSummary = this.cacheService.getLocal<TransactionSummary>(cacheKey);
    if (cachedSummary) {
      console.log('Transaction summary loaded from cache');
      return of(cachedSummary);
    }

    // Fetch from API
    const params = this.createParams(month);
    return this.http.get<TransactionSummary>(`${this.apiUrl}/transactions/summary/`, {
      headers: this.getHeaders(),
      params
    }).pipe(
      tap(summary => {
        // Cache the summary for 15 minutes
        this.cacheService.setLocal(cacheKey, summary, 15);
        console.log('Transaction summary cached');
      }),
      catchError(error => {
        console.error('Error fetching transaction summary:', error);
        const fallbackSummary: TransactionSummary = {
          total_transactions: 0,
          total_amount: 0,
          average_amount: 0,
          min_amount: 0,
          max_amount: 0
        };
        return of(fallbackSummary);
      })
    );
  }

  getTransactionsByCategory(month?: string): Observable<CategoryData> {
    const cacheKey = month ? `transactions_by_category_${month}` : 'transactions_by_category';
    
    // Try to get from cache first
    const cachedCategories = this.cacheService.getLocal<CategoryData>(cacheKey);
    if (cachedCategories) {
      console.log('Category data loaded from cache');
      return of(cachedCategories);
    }

    // Fetch from API
    const params = this.createParams(month);
    return this.http.get<CategoryData>(`${this.apiUrl}/transactions/by-category/`, {
      headers: this.getHeaders(),
      params
    }).pipe(
      tap(categories => {
        // Cache the categories for 15 minutes
        this.cacheService.setLocal(cacheKey, categories, 15);
        console.log('Category data cached');
      }),
      catchError(error => {
        console.error('Error fetching category data:', error);
        return of({});
      })
    );
  }

  getRecentTransactions(limit: number = 10): Observable<any[]> {
    const cacheKey = `recent_transactions_${limit}`;
    
    // Try to get from cache first
    const cachedTransactions = this.cacheService.getLocal<any[]>(cacheKey);
    if (cachedTransactions) {
      console.log('Recent transactions loaded from cache');
      return of(cachedTransactions);
    }

    // Fetch from API
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<any[]>(`${this.apiUrl}/transactions/`, {
      headers: this.getHeaders(),
      params
    }).pipe(
      tap(transactions => {
        // Cache the transactions for 5 minutes
        this.cacheService.setLocal(cacheKey, transactions, 5);
        console.log('Recent transactions cached');
      }),
      catchError(error => {
        console.error('Error fetching recent transactions:', error);
        return of([]);
      })
    );
  }

  getUserFamily(): Observable<any> {
    const cacheKey = 'user_family';
    
    // Try to get from cache first
    const cachedFamily = this.cacheService.getLocal<any>(cacheKey);
    if (cachedFamily) {
      console.log('User family loaded from cache');
      return of(cachedFamily);
    }

    // Fetch from API
    return this.http.get<any>(`${this.apiUrl}/family/user`, {
      headers: this.getHeaders()
    }).pipe(
      tap(family => {
        // Cache the family data for 30 minutes
        this.cacheService.setLocal(cacheKey, family, 30);
        console.log('User family cached');
      }),
      catchError(error => {
        console.error('Error fetching user family:', error);
        return of(null);
      })
    );
  }

  // Cache invalidation methods
  invalidateDashboardCache(month?: string): void {
    const cacheKey = month ? `dashboard_${month}` : 'dashboard';
    this.cacheService.removeLocal(cacheKey);
    console.log('Dashboard cache invalidated');
  }

  invalidateTransactionCache(month?: string): void {
    const summaryKey = month ? `transaction_summary_${month}` : 'transaction_summary';
    const categoryKey = month ? `transactions_by_category_${month}` : 'transactions_by_category';
    
    this.cacheService.removeLocal(summaryKey);
    this.cacheService.removeLocal(categoryKey);
    this.cacheService.removeLocal('recent_transactions_10');
    
    console.log('Transaction cache invalidated');
  }

  invalidateFamilyCache(): void {
    this.cacheService.removeLocal('user_family');
    console.log('Family cache invalidated');
  }

  // Clear all caches
  clearAllCaches(): void {
    this.cacheService.clearLocal();
    this.dashboardDataSubject.next(null);
    console.log('All dashboard caches cleared');
  }

  // Get cache statistics
  getCacheStats(): { local: number; session: number } {
    return this.cacheService.getCacheStats();
  }

  // Refresh dashboard data
  refreshDashboard(month?: string): Observable<DashboardData> {
    // Invalidate cache first
    this.invalidateDashboardCache(month);
    this.invalidateTransactionCache(month);
    
    // Fetch fresh data
    return this.getDashboardData(month);
  }
} 