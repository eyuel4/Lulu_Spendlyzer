import { Injectable, ComponentRef, ViewContainerRef, TemplateRef, Type } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export interface ModalConfig {
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  closable?: boolean;
  backdrop?: boolean;
  data?: any;
}

export interface ModalResult<T = any> {
  action?: string;
  data?: T;
}

@Injectable({
  providedIn: 'root'
})
export class ModalService {
  private modalSubject = new Subject<{ component: Type<any> | TemplateRef<any>, config?: ModalConfig }>();
  private resultSubject = new Subject<ModalResult | null>();
  private viewContainerRef?: ViewContainerRef;

  constructor() {}

  /**
   * Set the view container ref for modal rendering
   */
  setViewContainerRef(vcr: ViewContainerRef): void {
    this.viewContainerRef = vcr;
  }

  /**
   * Open a modal with a component
   */
  open<T = any>(component: Type<any>, config?: ModalConfig): Observable<ModalResult<T> | null> {
    this.modalSubject.next({ component, config });
    return this.resultSubject.asObservable();
  }

  /**
   * Get observable for modal open events
   */
  getModalEvents(): Observable<{ component: Type<any> | TemplateRef<any>, config?: ModalConfig }> {
    return this.modalSubject.asObservable();
  }

  /**
   * Close the modal with optional result
   */
  close(result?: ModalResult | null): void {
    this.resultSubject.next(result || null);
    this.resultSubject.complete();
    // Create new subject for next modal
    this.resultSubject = new Subject<ModalResult | null>();
  }
}

