import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface UserPreferences {
  defaultTransactionMethod?: string;
  theme?: 'light' | 'dark';
  notifications?: {
    email: boolean;
    push: boolean;
    sms: boolean;
  };
  dateFormat?: string;
  currency?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserPreferencesService {
  private apiUrl = `${environment.apiUrl}/user-preferences`;

  constructor(private http: HttpClient) {}

  getUserPreferences(): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(this.apiUrl);
  }

  updateUserPreferences(preferences: Partial<UserPreferences>): Observable<UserPreferences> {
    return this.http.patch<UserPreferences>(this.apiUrl, preferences);
  }

  updateDefaultTransactionMethod(method: string): Observable<UserPreferences> {
    return this.updateUserPreferences({ defaultTransactionMethod: method });
  }

  getDefaultTransactionMethod(): Observable<string | null> {
    return new Observable(observer => {
      this.getUserPreferences().subscribe({
        next: (preferences) => {
          observer.next(preferences.defaultTransactionMethod || null);
          observer.complete();
        },
        error: (error) => {
          console.error('Error fetching user preferences:', error);
          observer.next(null);
          observer.complete();
        }
      });
    });
  }
}
