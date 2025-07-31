import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss'
})
export class ResetPasswordComponent implements OnInit {
  resetForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';
  token = '';
  tokenValid = false;
  tokenExpired = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private http: HttpClient,
    private router: Router,
    private themeService: ThemeService
  ) {}

  ngOnInit(): void {
    // Force dark mode on initial load
    this.themeService.setTheme('dark');
    
    // Get token from query parameters
    this.token = this.route.snapshot.queryParamMap.get('token') || '';
    
    if (!this.token) {
      this.errorMessage = 'Invalid reset link. Missing token.';
      return;
    }

    // Validate token
    this.validateToken();
    
    this.initForm();
  }

  private initForm(): void {
    this.resetForm = this.fb.group({
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]]
    }, { validators: this.passwordMatchValidator });
  }

  private passwordMatchValidator(form: FormGroup) {
    const password = form.get('password');
    const confirmPassword = form.get('confirmPassword');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      confirmPassword.setErrors({ passwordMismatch: true });
      return { passwordMismatch: true };
    }
    
    if (confirmPassword && confirmPassword.errors) {
      delete confirmPassword.errors['passwordMismatch'];
      if (Object.keys(confirmPassword.errors).length === 0) {
        confirmPassword.setErrors(null);
      }
    }
    
    return null;
  }

  private validateToken(): void {
    // For now, we'll validate the token when the user submits
    // In a real implementation, you might want to validate it immediately
    this.tokenValid = true;
  }

  onSubmit(): void {
    if (this.resetForm.invalid || !this.tokenValid) return;
    
    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const { password } = this.resetForm.value;

    this.http.post('/api/auth/reset-password', {
      token: this.token,
      new_password: password
    }).subscribe({
      next: () => {
        this.loading = false;
        this.successMessage = 'Password reset successful! Redirecting to signin...';
        setTimeout(() => this.router.navigate(['/signin']), 2000);
      },
      error: (err) => {
        this.loading = false;
        if (err.error?.detail) {
          this.errorMessage = err.error.detail;
          if (err.error.detail.includes('expired')) {
            this.tokenExpired = true;
          }
        } else {
          this.errorMessage = 'An error occurred. Please try again.';
        }
      }
    });
  }
} 