import { Component, OnInit, OnDestroy, ViewChild, ViewContainerRef, ComponentRef, TemplateRef, Type } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ModalService, ModalConfig } from '../../services/modal.service';

@Component({
  selector: 'app-modal-container',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      *ngIf="isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      (click)="onBackdropClick($event)"
    >
      <div 
        class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        [ngClass]="sizeClasses"
        (click)="$event.stopPropagation()"
      >
        <!-- Modal Header -->
        <div *ngIf="config?.title || config?.closable !== false" class="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 *ngIf="config?.title" class="text-xl font-semibold text-slate-900 dark:text-white">
            {{ config?.title }}
          </h2>
          <button
            *ngIf="config?.closable !== false"
            (click)="onClose()"
            class="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors duration-200"
            aria-label="Close modal"
          >
            <svg class="w-5 h-5 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        <!-- Modal Body -->
        <div class="flex-1 overflow-y-auto">
          <ng-container #modalContent></ng-container>
        </div>
      </div>

      <!-- Backdrop -->
      <div 
        *ngIf="config?.backdrop !== false"
        class="fixed inset-0 bg-black bg-opacity-50 -z-10"
        (click)="onBackdropClick($event)"
      ></div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class ModalContainerComponent implements OnInit, OnDestroy {
  @ViewChild('modalContent', { read: ViewContainerRef }) modalContent!: ViewContainerRef;

  isOpen = false;
  config?: ModalConfig;
  componentRef?: ComponentRef<any>;
  private destroy$ = new Subject<void>();

  get sizeClasses(): string {
    const size = this.config?.size || 'md';
    const sizeMap: Record<string, string> = {
      'sm': 'max-w-sm',
      'md': 'max-w-md',
      'lg': 'max-w-lg',
      'xl': 'max-w-xl',
      '2xl': 'max-w-2xl',
      'full': 'max-w-full'
    };
    return sizeMap[size] || sizeMap['md'];
  }

  constructor(private modalService: ModalService) {}

  ngOnInit(): void {
    this.modalService.getModalEvents()
      .pipe(takeUntil(this.destroy$))
      .subscribe(({ component, config }) => {
        this.config = config;
        this.openModal(component);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.componentRef) {
      this.componentRef.destroy();
    }
  }

  private openModal(component: Type<any> | TemplateRef<any>): void {
    this.isOpen = true;
    this.modalContent.clear();

    if (component instanceof TemplateRef) {
      // Handle template ref if needed
      this.modalContent.createEmbeddedView(component);
    } else {
      // Create component
      this.componentRef = this.modalContent.createComponent(component);
      
      // Pass config data to component if it has a data input
      if (this.config?.data && this.componentRef.instance) {
        if ('data' in this.componentRef.instance) {
          this.componentRef.instance.data = this.config.data;
        }
        // Trigger change detection if component has ngOnChanges
        if (typeof this.componentRef.instance.ngOnChanges === 'function') {
          this.componentRef.instance.ngOnChanges({
            data: {
              currentValue: this.config.data,
              previousValue: undefined,
              firstChange: true,
              isFirstChange: () => true
            }
          });
        }
        // Also trigger ngOnInit if component implements it
        if (typeof this.componentRef.instance.ngOnInit === 'function') {
          this.componentRef.instance.ngOnInit();
        }
      }

      // Subscribe to close event if component emits it
      if (this.componentRef.instance && 'close' in this.componentRef.instance) {
        const closeSubject = this.componentRef.instance.close;
        if (closeSubject && typeof closeSubject.subscribe === 'function') {
          closeSubject
            .pipe(takeUntil(this.destroy$))
            .subscribe((result: any) => {
              this.onClose(result);
            });
        }
      }
    }
  }

  onClose(result?: any): void {
    this.isOpen = false;
    if (this.componentRef) {
      this.componentRef.destroy();
      this.componentRef = undefined;
    }
    this.modalContent.clear();
    this.modalService.close(result);
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget && this.config?.closable !== false) {
      this.onClose(null);
    }
  }
}

