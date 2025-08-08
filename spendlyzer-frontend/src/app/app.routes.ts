import { Routes } from '@angular/router';
import { SignupComponent } from './pages/signup/signup.component';
import { SigninComponent } from './pages/signin/signin.component';
import { ForgotPasswordComponent } from './pages/forgot-password/forgot-password.component';
import { InviteSignupComponent } from './pages/invite-signup/invite-signup.component';
import { ResetPasswordComponent } from './pages/reset-password/reset-password.component';
import { ProfileComponent } from './pages/profile/profile.component';

export const routes: Routes = [
  { path: '', redirectTo: '/signin', pathMatch: 'full' },
  { path: 'signup', component: SignupComponent },
  { path: 'signin', component: SigninComponent },
  { 
    path: 'two-factor-verification', 
    loadComponent: () => import('./pages/two-factor-verification/two-factor-verification.component').then(m => m.TwoFactorVerificationComponent)
  },
  { path: 'forgot-password', component: ForgotPasswordComponent },
  { path: 'reset-password', component: ResetPasswordComponent },
  { 
    path: 'dashboard', 
    loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
    // TODO: Add auth guard here
  },
  { path: 'invite-signup', component: InviteSignupComponent },
  { path: 'invite/complete/:token', component: InviteSignupComponent },
  { 
    path: 'social-login', 
    loadComponent: () => import('./pages/social-login/social-login.component').then(m => m.SocialLoginComponent)
  },
  { 
    path: 'questionnaire', 
    loadComponent: () => import('./pages/questionnaire/questionnaire.component').then(m => m.QuestionnaireComponent)
  },
  { 
    path: 'family-setup', 
    loadComponent: () => import('./pages/family-setup/family-setup.component').then(m => m.FamilySetupComponent)
  },
  { 
    path: 'account', 
    loadComponent: () => import('./pages/account-settings/account-settings.component').then(m => m.AccountSettingsComponent)
  },
  { 
    path: 'profile', 
    loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent)
  },
  {
    path: 'billing',
    loadComponent: () => import('./pages/billing-subscription/billing-subscription.component').then(m => m.BillingSubscriptionComponent)
  },
  {
    path: 'request-feature',
    loadComponent: () => import('./pages/request-feature/request-feature.component').then(m => m.RequestFeatureComponent)
  },
  { path: '**', redirectTo: '/signin' }
];
