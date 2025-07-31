import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-invite-signup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './invite-signup.component.html',
  styleUrl: './invite-signup.component.scss'
})
export class InviteSignupComponent implements OnInit {
  inviteForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';
  token = '';
  inviterName = '';
  inviteeFirstName = '';
  inviteeLastName = '';
  inviteeEmail = '';
  inviteeRole = '';

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
    // Handle both route parameters and query parameters
    this.token = this.route.snapshot.paramMap.get('token') || 
                 this.route.snapshot.queryParamMap.get('token') || '';
    
    if (!this.token) {
      this.errorMessage = 'Invalid invitation link.';
      return;
    }

    // Fetch invite details
    this.http.get<any>(`/api/family/invite/accept/${this.token}`).subscribe({
      next: (data) => {
        this.inviteeFirstName = data.first_name;
        this.inviteeLastName = data.last_name;
        this.inviteeEmail = data.email;
        this.inviteeRole = data.role;
        this.inviterName = data.inviter || '';
        this.inviteForm = this.fb.group({
          first_name: [{ value: data.first_name, disabled: true }],
          last_name: [{ value: data.last_name, disabled: true }],
          email: [{ value: data.email, disabled: true }],
          username: [data.email.split('@')[0], [Validators.required, Validators.minLength(3)]],
          password: ['', [Validators.required, Validators.minLength(6)]]
        });
      },
      error: () => {
        this.errorMessage = 'This invitation is invalid or expired.';
      }
    });
  }

  onSubmit(): void {
    if (this.inviteForm.invalid) return;
    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const { username, password } = this.inviteForm.getRawValue();

    this.http.post('/api/family/register-invitee', {
      token: this.token,
      username,
      password
    }).subscribe({
      next: () => {
        this.successMessage = 'Account created! You can now sign in.';
        setTimeout(() => this.router.navigate(['/signin']), 2000);
      },
      error: (err) => {
        this.loading = false;
        if (err.error?.detail) {
          this.errorMessage = err.error.detail;
        } else {
          this.errorMessage = 'An error occurred. Please try again.';
        }
      }
    });
  }
} 