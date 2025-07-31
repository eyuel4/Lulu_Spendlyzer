import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class FeatureRequestService {
  private apiUrl = '/api/feature-requests';

  constructor(private http: HttpClient) {}

  submitFeatureRequest(description: string): Observable<any> {
    return this.http.post(this.apiUrl, { description });
  }
} 