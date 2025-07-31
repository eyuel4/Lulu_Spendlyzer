import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent implements OnInit {
  resetForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.resetForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]]
    });
  }

  onSubmit(): void {
    if (this.resetForm.valid) {
      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const email = this.resetForm.value.email;

      this.authService.forgotPassword(email).subscribe({
        next: (response) => {
          this.loading = false;
          this.successMessage = 'If the email is registered, a password reset link has been sent.';
          this.resetForm.reset();
        },
        error: (error) => {
          this.loading = false;
          if (error.error?.detail) {
            this.errorMessage = error.error.detail;
          } else {
            this.errorMessage = 'An error occurred. Please try again.';
          }
        }
      });
    }
  }
}
