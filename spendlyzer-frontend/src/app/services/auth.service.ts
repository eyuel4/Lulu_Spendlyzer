import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap, catchError, map } from 'rxjs/operators';
import { CacheService } from './cache.service';
// @ts-ignore
import UAParser from 'ua-parser-js';

export interface SignupRequest {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface SigninRequest {
  login: string; // username or email
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  requires_2fa?: boolean;
  method?: string;
  temp_token?: string;
  message?: string;
  trusted_device_token?: string;
  trusted_device_expires?: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000'; // Update with your backend URL
  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  public get currentUserValue() {
    return this.currentUserSubject.value;
  }

  // HTTP headers for requests
  private httpHeaders = new HttpHeaders({
    'Content-Type': 'application/json'
  });

  constructor(
    private http: HttpClient,
    private cacheService: CacheService
  ) {
    this.loadStoredUser();
  }

  private isBrowser(): boolean {
    return typeof window !== 'undefined' && !!window.localStorage;
  }

  private loadStoredUser(): void {
    if (this.isBrowser()) {
      let userJson: string | null = null;
      if (typeof window !== 'undefined' && window.localStorage) {
        userJson = localStorage.getItem('user');
      }
      if (userJson) {
        this.currentUserSubject.next(JSON.parse(userJson));
      }
      
      // Check for token in URL (from Google OAuth)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      if (token) {
        // Store the token and decode user
        localStorage.setItem('access_token', token);
        const user = this.decodeToken(token);
        this.currentUserSubject.next(user);
        
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }

  private decodeToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(window.atob(base64));
    } catch (error) {
      return null;
    }
  }

  signup(userData: SignupRequest): Observable<AuthResponse> {
    const parser = new (UAParser as any)();
    const uaResult = parser.getResult();
    const deviceInfo = `${uaResult.browser.name} on ${uaResult.os.name} ${uaResult.os.version}`;
    const headers = this.httpHeaders
      .set('Origin', 'http://localhost:4200')
      .set('X-Device-Info', deviceInfo);
    return this.http.post<AuthResponse>(`${this.apiUrl}/auth/signup`, userData, {
      headers: headers
    }).pipe(
      tap((response: AuthResponse) => {
        this.handleAuthResponse(response);
      })
    );
  }

  signin(credentials: SigninRequest): Observable<AuthResponse> {
    const parser = new (UAParser as any)();
    const uaResult = parser.getResult();
    const deviceInfo = `${uaResult.browser.name} on ${uaResult.os.name} ${uaResult.os.version}`;
    const headers = this.httpHeaders.set('X-Device-Info', deviceInfo);
    
    const requestOptions: any = {
      headers: headers,
      withCredentials: true // Include cookies in the request
    };
    
    return this.http.post<AuthResponse>(`${this.apiUrl}/auth/signin`, credentials, requestOptions).pipe(
      map((event: any) => {
        // Extract the response body from the HttpEvent
        if (event.body) {
          return event.body;
        }
        return event;
      }),
      tap((response: AuthResponse) => {
        this.handleAuthResponse(response);
      })
    );
  }

  forgotPassword(email: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/forgot-password`, { email }, {
      headers: this.httpHeaders
    });
  }

  private handleAuthResponse(response: AuthResponse): void {
    if (this.isBrowser()) {
      if (typeof window !== 'undefined' && window.localStorage) {
        if (response.requires_2fa) {
          // Store temporary token for 2FA verification
          localStorage.setItem('temp_2fa_token', response.temp_token || '');
          // Store 2FA method from response
          if (response.method) {
            localStorage.setItem('2fa_method', response.method);
          }
        } else {
          localStorage.setItem('access_token', response.access_token);
        }
      }
    }
    
    if (response.requires_2fa) {
      // Don't set current user yet, wait for 2FA verification
      return;
    }
    
    const user = this.decodeToken(response.access_token);
    this.currentUserSubject.next(user);
  }

  logout(): void {
    if (this.isBrowser()) {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.removeItem('access_token');
      }
    }
    this.currentUserSubject.next(null);
  }

  isAuthenticated(): boolean {
    if (!this.isBrowser()) return false;
    let token: string | null = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      token = localStorage.getItem('access_token');
    }
    if (!token) return false;
    
    const payload = this.decodeToken(token);
    if (!payload) return false;
    
    // Check if token is expired
    const currentTime = Date.now() / 1000;
    return payload.exp > currentTime;
  }

  getToken(): string | null {
    if (this.isBrowser()) {
      if (typeof window !== 'undefined' && window.localStorage) {
        return localStorage.getItem('access_token');
      }
    }
    return null;
  }

  fetchCurrentUser(): Observable<any> {
    const token = this.getToken();
    if (!token) return new Observable(observer => observer.error('No token'));
    const headers = this.httpHeaders.set('Authorization', `Bearer ${token}`);
    return this.http.get<any>(`${this.apiUrl}/auth/me`, { headers }).pipe(
      tap(user => {
        if (this.isBrowser()) {
          if (typeof window !== 'undefined' && window.localStorage) {
            localStorage.setItem('user', JSON.stringify(user));
          }
        }
        this.currentUserSubject.next(user);
      })
    );
  }

  saveUserPreferences(preferences: any): Observable<any> {
    const token = this.getToken();
    if (!token) return new Observable(observer => observer.error('No token'));
    const headers = this.httpHeaders.set('Authorization', `Bearer ${token}`);

    return this.http.post<any>(`${this.apiUrl}/auth/preferences`, preferences, { headers }).pipe(
      tap(response => {
        // Invalidate cache when preferences are saved
        this.cacheService.removeLocal('user_preferences');
        console.log('User preferences cache invalidated');
      })
    );
  }

  getUserPreferences(): Observable<any> {
    const token = this.getToken();
    if (!token) return new Observable(observer => observer.error('No token'));
    
    // Try to get from cache first
    const cachedPreferences = this.cacheService.getLocal('user_preferences');
    if (cachedPreferences) {
      console.log('User preferences loaded from cache');
      return of(cachedPreferences);
    }
    
    const headers = this.httpHeaders.set('Authorization', `Bearer ${token}`);
    return this.http.get<any>(`${this.apiUrl}/auth/preferences`, { headers }).pipe(
      tap(preferences => {
        // Cache the preferences for 30 minutes
        this.cacheService.setLocal('user_preferences', preferences, 30);
      }),
      catchError(error => {
        console.error('Error fetching user preferences:', error);
        return of({ has_preferences: false });
      })
    );
  }

  // 2FA Methods
  verify2FA(code: string, rememberDevice: boolean = false): Observable<AuthResponse> {
    const tempToken = this.getTemp2FAToken();
    if (!tempToken) return new Observable(observer => observer.error('No temporary 2FA token'));
    
    const requestBody = { code, remember_device: rememberDevice };
    const headers = this.httpHeaders.set('Authorization', `Bearer ${tempToken}`);
    
    console.log('DEBUG: Sending 2FA verification request:');
    console.log('DEBUG: URL:', `${this.apiUrl}/auth/verify-2fa`);
    console.log('DEBUG: Headers:', headers);
    console.log('DEBUG: Request body:', requestBody);
    console.log('DEBUG: Temp token (first 20 chars):', tempToken.substring(0, 20) + '...');
    
    return this.http.post<AuthResponse>(`${this.apiUrl}/auth/verify-2fa`, requestBody, { 
      headers
    }).pipe(
      tap((response: AuthResponse) => {
        console.log('DEBUG: 2FA verification successful:', response);
        this.handleAuthResponse(response);
        
        // Handle trusted device token if provided
        if (response.trusted_device_token) {
          // Trusted device token is now set as HTTP-only cookie by the backend
          console.log('DEBUG: Trusted device token received and set as cookie');
        }
        
        // Clear temporary token
        if (this.isBrowser() && typeof window !== 'undefined' && window.localStorage) {
          localStorage.removeItem('temp_2fa_token');
        }
      }),
      catchError(error => {
        console.error('DEBUG: 2FA verification error:', error);
        console.error('DEBUG: Error status:', error.status);
        console.error('DEBUG: Error message:', error.message);
        console.error('DEBUG: Error response:', error.error);
        throw error;
      })
    );
  }

  sendSMSCode(): Observable<any> {
    const tempToken = this.getTemp2FAToken();
    if (!tempToken) return new Observable(observer => observer.error('No temporary 2FA token'));
    
    const headers = this.httpHeaders.set('Authorization', `Bearer ${tempToken}`);
    return this.http.post<any>(`${this.apiUrl}/auth/send-sms-code`, {}, { headers });
  }

  sendEmailCode(): Observable<any> {
    const tempToken = this.getTemp2FAToken();
    if (!tempToken) return new Observable(observer => observer.error('No temporary 2FA token'));
    
    const headers = this.httpHeaders.set('Authorization', `Bearer ${tempToken}`);
    return this.http.post<any>(`${this.apiUrl}/auth/send-email-code`, {}, { headers });
  }

  private getTemp2FAToken(): string | null {
    if (this.isBrowser() && typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem('temp_2fa_token');
    }
    return null;
  }

  is2FARequired(): boolean {
    return !!this.getTemp2FAToken();
  }


}
