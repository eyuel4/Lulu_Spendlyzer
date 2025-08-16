import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UserPreferencesService } from '../../services/user-preferences.service';

export interface TransactionOption {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  bgColor: string;
}

@Component({
  selector: 'app-add-transaction-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './add-transaction-modal.component.html',
  styleUrls: ['./add-transaction-modal.component.scss']
})
export class AddTransactionModalComponent {
  @Input() isOpen = false;
  @Output() closeModal = new EventEmitter<void>();
  @Output() optionSelected = new EventEmitter<{option: string, setAsDefault: boolean}>();

  selectedOption: string = '';
  setAsDefault: boolean = false;

  constructor(private userPreferencesService: UserPreferencesService) {}

  transactionOptions: TransactionOption[] = [
    {
      id: 'bank-api',
      title: 'Bank',
      description: 'Connect to your bank through API for automatic transaction sync',
      icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z',
      color: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-100 dark:bg-blue-900'
    },
    {
      id: 'upload-statement',
      title: 'Upload Statement',
      description: 'Upload a bank statement file (CSV, PDF, or Excel)',
      icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12',
      color: 'text-emerald-600 dark:text-emerald-400',
      bgColor: 'bg-emerald-100 dark:bg-emerald-900'
    },
    {
      id: 'manual',
      title: 'Manual Transaction',
      description: 'Add a transaction manually by entering details yourself',
      icon: 'M12 6v6m0 0v6m0-6h6m-6 0H6',
      color: 'text-indigo-600 dark:text-indigo-400',
      bgColor: 'bg-indigo-100 dark:bg-indigo-900'
    }
  ];

  onOptionSelect(optionId: string): void {
    this.selectedOption = optionId;
  }

  onContinue(): void {
    if (this.selectedOption) {
      // If user wants to set as default, make API call
      if (this.setAsDefault) {
        this.userPreferencesService.updateDefaultTransactionMethod(this.selectedOption).subscribe({
          next: (response) => {
            console.log('Default transaction method saved:', response);
          },
          error: (error) => {
            console.error('Error saving default transaction method:', error);
          }
        });
      }

      this.optionSelected.emit({
        option: this.selectedOption,
        setAsDefault: this.setAsDefault
      });
      this.closeModal.emit();
    }
  }

  onClose(): void {
    this.closeModal.emit();
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.onClose();
    }
  }
}
