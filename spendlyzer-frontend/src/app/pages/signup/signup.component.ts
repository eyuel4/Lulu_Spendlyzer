import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './signup.component.html',
  styleUrl: './signup.component.scss'
})
export class SignupComponent implements OnInit {
  signupForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.signupForm = this.fb.group({
      firstName: ['', [Validators.required]],
      lastName: ['', [Validators.required]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]]
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(control: AbstractControl): { [key: string]: boolean } | null {
    const password = control.get('password');
    const confirmPassword = control.get('confirmPassword');
    
    if (password && confirmPassword && password.value !== confirmPassword.value) {
      return { 'passwordMismatch': true };
    }
    
    return null;
  }

  onSubmit(): void {
    if (this.signupForm.valid) {
      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const formValue = this.signupForm.value;
      const userData = {
        username: formValue.email,
        first_name: formValue.firstName,
        last_name: formValue.lastName,
        email: formValue.email,
        password: formValue.password
      };

      this.authService.signup(userData).subscribe({
        next: (response) => {
          this.loading = false;
          this.successMessage = 'Account created successfully! Redirecting to questionnaire...';
          setTimeout(() => {
            this.router.navigate(['/questionnaire']);
          }, 1500);
        },
        error: (error) => {
          this.loading = false;
          if (error.error?.detail) {
            this.errorMessage = error.error.detail;
          } else {
            this.errorMessage = 'An error occurred during signup. Please try again.';
          }
        }
      });
    }
  }

  onGoogleSignUp(): void {
    window.location.href = '/api/auth/google/login';
  }
}
