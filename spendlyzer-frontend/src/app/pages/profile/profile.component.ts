import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ProfileService } from '../../services/profile.service';
import { UserProfile } from '../../models/user-profile.model';
import { ThemeService } from '../../services/theme.service';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-profile',
  standalone: true,
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
  imports: [CommonModule, ReactiveFormsModule]
})
export class ProfileComponent implements OnInit {
  profileForm!: FormGroup;
  loading = true;
  error: string | null = null;
  success: boolean = false;
  userProfile!: UserProfile;
  theme: 'light' | 'dark' = 'light';

  constructor(
    private fb: FormBuilder,
    private profileService: ProfileService,
    private themeService: ThemeService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.themeService.currentTheme$.subscribe((theme: 'light' | 'dark') => this.theme = theme);
    this.profileForm = this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      username: ['', Validators.required]
    });
    this.loadProfile();
  }

  loadProfile(): void {
    this.loading = true;
    this.profileService.getProfile().subscribe({
      next: (profile) => {
        this.userProfile = profile;
        this.profileForm.patchValue(profile);
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load profile.';
        this.loading = false;
      }
    });
  }

  onSubmit(): void {
    if (this.profileForm.invalid) return;
    this.loading = true;
    this.profileService.updateProfile({ ...this.userProfile, ...this.profileForm.value }).subscribe({
      next: (profile) => {
        this.userProfile = profile;
        this.success = true;
        this.loading = false;
        setTimeout(() => this.success = false, 2000);
      },
      error: (err) => {
        this.error = 'Failed to update profile.';
        this.loading = false;
      }
    });
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }

  get f() { return this.profileForm.controls; }

  get isGoogleUser(): boolean {
    return this.userProfile?.authProvider === 'google';
  }
} 