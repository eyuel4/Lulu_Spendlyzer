import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { isPlatformBrowser } from '@angular/common';

@Component({
  selector: 'app-social-login',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div class="max-w-md w-full space-y-8">
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <!-- Loading State -->
          <div *ngIf="loading" class="text-center">
            <div class="mx-auto h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center mb-6">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Signing you in...</h2>
            <p class="text-gray-600">Please wait while we authenticate your account</p>
          </div>

          <!-- Success State -->
          <div *ngIf="!loading && user" class="text-center">
            <div class="mx-auto h-16 w-16 bg-green-100 rounded-full flex items-center justify-center mb-6">
              <svg class="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">
              Welcome, {{ user.first_name || user.username || user.email }}!
            </h2>
            <p *ngIf="isNewUser" class="text-gray-600 mb-4">Setting up your account...</p>
            <p *ngIf="!isNewUser" class="text-gray-600 mb-4">Redirecting to your dashboard...</p>
            <div class="flex items-center justify-center space-x-2">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span class="text-sm text-gray-500">Please wait</span>
            </div>
          </div>

          <!-- Error State -->
          <div *ngIf="!loading && error" class="text-center">
            <div class="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
              <svg class="h-8 w-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Authentication Error</h2>
            <p class="text-gray-600 mb-6">{{ error }}</p>
            <button 
              (click)="goToSignin()"
              class="w-full px-6 py-3 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
            >
              Go to Sign In
            </button>
          </div>

          <!-- No Token State -->
          <div *ngIf="!loading && !user && !error" class="text-center">
            <div class="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-6">
              <svg class="h-8 w-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
              </svg>
            </div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">No Authentication Token</h2>
            <p class="text-gray-600 mb-6">No authentication token was received. Please try signing in again.</p>
            <button 
              (click)="goToSignin()"
              class="w-full px-6 py-3 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
            >
              Go to Sign In
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
    }
  `]
})
export class SocialLoginComponent implements OnInit {
  loading = true;
  user: any = null;
  error: string | null = null;
  isNewUser = false;

  constructor(
    private router: Router, 
    private authService: AuthService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit(): void {
    console.log('SocialLoginComponent initialized');
    
    // Only access window if we're in a browser environment
    if (isPlatformBrowser(this.platformId)) {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      const isNewUser = params.get('new_user') === 'true';
      console.log('Token from URL:', token ? 'Present' : 'Missing');
      console.log('Is new user:', isNewUser);
      
      if (token) {
        console.log('Setting token in localStorage');
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem('access_token', token);
        }
        
        console.log('Fetching current user...');
        this.authService.fetchCurrentUser().subscribe({
          next: (user) => {
            console.log('User fetched successfully:', user);
            this.user = user;
            this.loading = false;
            this.isNewUser = isNewUser;
            
            setTimeout(() => {
              if (isNewUser) {
                console.log('New user - checking if questionnaire completed...');
                this.checkUserPreferences();
              } else {
                console.log('Existing user - navigating to dashboard...');
                this.router.navigate(['/dashboard']);
              }
            }, 1200);
          },
          error: (error) => {
            console.error('Error fetching user:', error);
            this.error = 'Failed to authenticate. Please try signing in again.';
            this.loading = false;
          }
        });
      } else {
        console.log('No token found, redirecting to signin');
        this.error = 'No authentication token received.';
        this.loading = false;
      }
    } else {
      // Server-side rendering - set error state
      this.error = 'Please wait while the page loads...';
      this.loading = false;
    }
  }

  goToSignin(): void {
    this.router.navigate(['/signin']);
  }

  private checkUserPreferences(): void {
    this.authService.getUserPreferences().subscribe({
      next: (response) => {
        if (response.has_preferences) {
          console.log('User has preferences - navigating to dashboard...');
          this.router.navigate(['/dashboard']);
        } else {
          console.log('User has no preferences - navigating to questionnaire...');
          this.router.navigate(['/questionnaire']);
        }
      },
      error: (error) => {
        console.error('Error checking user preferences:', error);
        // If we can't check preferences, default to questionnaire
        this.router.navigate(['/questionnaire']);
      }
    });
  }
} 