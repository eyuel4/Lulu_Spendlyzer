import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-signin',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './signin.component.html',
  styleUrl: './signin.component.scss'
})
export class SigninComponent implements OnInit {
  signinForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.signinForm = this.fb.group({
      login: ['', [Validators.required]], // username or email
      password: ['', [Validators.required]]
    });
  }

  onSubmit(): void {
    if (this.signinForm.valid) {
      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const credentials = {
        login: this.signinForm.value.login,
        password: this.signinForm.value.password
      };

      this.authService.signin(credentials).subscribe({
        next: (response) => {
          this.loading = false;
          
          if (response.requires_2fa) {
            // Store 2FA method for the verification page
            if (typeof window !== 'undefined' && window.localStorage) {
              localStorage.setItem('2fa_method', response.method || 'authenticator');
            }
            // Navigate to 2FA verification page
            this.router.navigate(['/two-factor-verification']);
          } else {
            this.successMessage = 'Sign in successful! Redirecting to dashboard...';
            // Check user preferences before navigating
            setTimeout(() => {
              this.checkUserPreferences();
            }, 1500);
          }
        },
        error: (error) => {
          this.loading = false;
          if (error.error?.detail) {
            this.errorMessage = error.error.detail;
          } else {
            this.errorMessage = 'Invalid credentials. Please try again.';
          }
        }
      });
    }
  }

  onGoogleSignIn(): void {
    window.location.href = '/api/auth/google/login';
  }

  private checkUserPreferences(): void {
    this.authService.getUserPreferences().subscribe({
      next: (response) => {
        if (response.has_preferences) {
          console.log('User has preferences - navigating to dashboard...');
          this.router.navigate(['/dashboard']);
        } else {
          console.log('User has no preferences - navigating to questionnaire...');
          let skipped = false;
          if (typeof window !== 'undefined' && window.localStorage) {
            skipped = localStorage.getItem('questionnaire_skipped') === 'true';
          }
          if (skipped) {
            this.router.navigate(['/dashboard']);
          } else {
            this.router.navigate(['/questionnaire']);
          }
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
