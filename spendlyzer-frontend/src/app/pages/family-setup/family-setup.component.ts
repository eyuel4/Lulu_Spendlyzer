import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { AuthService } from '../../services/auth.service';

interface FamilyMember {
  email: string;
  first_name: string;
  last_name: string;
  role: string;
}

@Component({
  selector: 'app-family-setup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './family-setup.component.html'
})
export class FamilySetupComponent implements OnInit {
  familyForm!: FormGroup;
  loading = false;
  errorMessage = '';
  successMessage = '';

  get invitees(): FormArray {
    return this.familyForm.get('invitees') as FormArray;
  }

  constructor(
    private router: Router, 
    private authService: AuthService,
    private http: HttpClient,
    private fb: FormBuilder
  ) {}

  ngOnInit(): void {
    this.initForm();
  }

  private initForm(): void {
    this.familyForm = this.fb.group({
      family_name: ['', Validators.required],
      invitees: this.fb.array([])
    });
  }

  addInvitee(): void {
    this.invitees.push(this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      role: ['spouse', Validators.required]
    }));
  }

  removeInvitee(index: number): void {
    this.invitees.removeAt(index);
  }

  onSubmit(): void {
    if (this.familyForm.valid) {
      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const formValue = this.familyForm.value;
      const familyData = {
        family_name: formValue.family_name,
        invitees: formValue.invitees
      };

      this.http.post('http://localhost:8000/auth/setup-family', familyData, {
        headers: new HttpHeaders({
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authService.getToken()}`
        })
      }).subscribe({
        next: (response) => {
          this.loading = false;
          this.successMessage = 'Family setup completed successfully!';
          setTimeout(() => {
            this.router.navigate(['/dashboard']);
          }, 2000);
        },
        error: (error) => {
          this.loading = false;
          if (error.error?.detail) {
            this.errorMessage = error.error.detail;
          } else {
            this.errorMessage = 'An error occurred during family setup. Please try again.';
          }
        }
      });
    }
  }

  skipFamilySetup(): void {
    this.router.navigate(['/dashboard']);
  }
} 