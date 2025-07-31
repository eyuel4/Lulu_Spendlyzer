import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FeatureRequestService } from '../../services/feature-request.service';

@Component({
  selector: 'app-request-feature',
  standalone: true,
  templateUrl: './request-feature.component.html',
  styleUrls: ['./request-feature.component.scss'],
  imports: [CommonModule, ReactiveFormsModule],
  providers: [FeatureRequestService]
})
export class RequestFeatureComponent {
  featureForm: FormGroup;
  loading = false;
  success: boolean = false;
  error: string | null = null;

  constructor(private fb: FormBuilder, private router: Router, private featureRequestService: FeatureRequestService) {
    this.featureForm = this.fb.group({
      description: ['', [Validators.required, Validators.minLength(10)]]
    });
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }

  async onSubmit() {
    if (this.featureForm.invalid) return;
    this.loading = true;
    this.error = null;
    this.success = false;
    const desc = this.featureForm.value.description;
    this.featureRequestService.submitFeatureRequest(desc).subscribe({
      next: () => {
        this.loading = false;
        this.success = true;
        this.featureForm.reset();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Failed to submit feature request.';
      }
    });
  }
} 