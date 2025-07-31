import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BillingService, SubscriptionSummary } from '../../services/billing.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-billing-subscription',
  standalone: true,
  templateUrl: './billing-subscription.component.html',
  styleUrls: ['./billing-subscription.component.scss'],
  imports: [CommonModule]
})
export class BillingSubscriptionComponent implements OnInit {
  loading = true;
  error: string | null = null;
  subscription: SubscriptionSummary | null = null;

  constructor(private billingService: BillingService, private router: Router) {}

  ngOnInit(): void {
    this.billingService.getSummary().subscribe({
      next: (summary: SubscriptionSummary) => {
        this.subscription = summary;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = 'Failed to load billing info.';
        this.loading = false;
      }
    });
  }

  openSubscribeModal() {
    // For demo, just subscribe to 'Pro Plan' with a mock payment method
    this.loading = true;
    this.billingService.subscribe('Pro Plan', 'Visa •••• 4242').subscribe({
      next: (_: any) => {
        this.refreshSummary();
      },
      error: (err: any) => {
        this.error = 'Failed to subscribe.';
        this.loading = false;
      }
    });
  }

  openManageModal() {
    // For demo, just cancel the subscription
    if (confirm('Are you sure you want to cancel your subscription?')) {
      this.loading = true;
      this.billingService.cancel().subscribe({
        next: (_: any) => {
          this.refreshSummary();
        },
        error: (err: any) => {
          this.error = 'Failed to cancel subscription.';
          this.loading = false;
        }
      });
    }
  }

  goBack() {
    this.router.navigate(['/dashboard']);
  }

  private refreshSummary() {
    this.billingService.getSummary().subscribe({
      next: (summary: SubscriptionSummary) => {
        this.subscription = summary;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = 'Failed to load billing info.';
        this.loading = false;
      }
    });
  }
} 