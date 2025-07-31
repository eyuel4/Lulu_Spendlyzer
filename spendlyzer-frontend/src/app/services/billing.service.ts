import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';

export interface SubscriptionSummary {
  planName: string;
  status: 'active' | 'inactive' | 'canceled';
  renewalDate?: string;
  paymentMethod?: string;
  invoices: { date: string; amount: number; status: string }[];
}

@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly apiUrl = '/api/billing/summary';
  private readonly subscribeUrl = '/api/billing/subscribe';
  private readonly updateUrl = '/api/billing/update';
  private readonly cancelUrl = '/api/billing/cancel';

  constructor(private http: HttpClient) {}

  getSummary(): Observable<SubscriptionSummary> {
    return this.http.get<SubscriptionSummary>(this.apiUrl);
  }

  subscribe(planName: string, paymentMethod?: string): Observable<any> {
    return this.http.post(this.subscribeUrl, { plan_name: planName, payment_method: paymentMethod });
  }

  update(planName?: string, paymentMethod?: string): Observable<any> {
    return this.http.post(this.updateUrl, { plan_name: planName, payment_method: paymentMethod });
  }

  cancel(): Observable<any> {
    return this.http.post(this.cancelUrl, {});
  }
} 