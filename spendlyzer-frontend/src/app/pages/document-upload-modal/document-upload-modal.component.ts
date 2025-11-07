import { Component, EventEmitter, Input, Output, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DocumentUploadService } from '../../services/document-upload.service';

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  file?: File;
  url?: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

@Component({
  selector: 'app-document-upload-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './document-upload-modal.component.html',
  styleUrls: ['./document-upload-modal.component.scss']
})
export class DocumentUploadModalComponent implements OnInit, OnChanges {
  @Input() isOpen = false;
  @Output() closeModal = new EventEmitter<void>();
  @Output() filesUploaded = new EventEmitter<UploadedFile[]>();

  selectedFiles: UploadedFile[] = [];
  fileUrl: string = '';
  isDragOver: boolean = false;
  isUploading: boolean = false;
  uploadProgress: number = 0;
  errorMessage: string = '';

  // Allowed file types
  private readonly allowedTypes = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
    'application/vnd.ms-excel', // .xls
    'application/pdf' // .pdf
  ];

  private readonly allowedExtensions = ['.xlsx', '.xls', '.pdf'];

  constructor(private documentUploadService: DocumentUploadService) {}

  ngOnInit(): void {
    // Initialize component
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['isOpen'] && this.isOpen) {
      this.resetState();
    }
  }

  private resetState(): void {
    this.selectedFiles = [];
    this.fileUrl = '';
    this.isDragOver = false;
    this.isUploading = false;
    this.uploadProgress = 0;
    this.errorMessage = '';
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFiles(Array.from(files));
    }
  }

  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFiles(Array.from(input.files));
    }
  }

  private handleFiles(files: File[]): void {
    this.errorMessage = '';
    
    for (const file of files) {
      if (this.validateFile(file)) {
        const uploadedFile: UploadedFile = {
          id: this.generateId(),
          name: file.name,
          size: file.size,
          type: file.type,
          file: file,
          status: 'pending'
        };
        
        // Check if file already exists
        if (!this.selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
          this.selectedFiles.push(uploadedFile);
        }
      }
    }
  }

  private validateFile(file: File): boolean {
    // Check file type
    if (!this.allowedTypes.includes(file.type)) {
      // Check by extension as fallback
      const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      if (!this.allowedExtensions.includes(extension)) {
        this.errorMessage = `File "${file.name}" is not supported. Only Excel (.xlsx, .xls) and PDF (.pdf) files are allowed.`;
        return false;
      }
    }

    // Check file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      this.errorMessage = `File "${file.name}" is too large. Maximum file size is 10MB.`;
      return false;
    }

    return true;
  }

  addFileFromUrl(): void {
    if (!this.fileUrl.trim()) {
      this.errorMessage = 'Please enter a valid file URL.';
      return;
    }

    // Basic URL validation
    try {
      new URL(this.fileUrl);
    } catch {
      this.errorMessage = 'Please enter a valid URL.';
      return;
    }

    // Extract filename from URL
    const urlParts = this.fileUrl.split('/');
    const filename = urlParts[urlParts.length - 1];
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));

    if (!this.allowedExtensions.includes(extension)) {
      this.errorMessage = 'URL must point to an Excel (.xlsx, .xls) or PDF (.pdf) file.';
      return;
    }

    const uploadedFile: UploadedFile = {
      id: this.generateId(),
      name: filename,
      size: 0, // Unknown size for URL files
      type: this.getMimeTypeFromExtension(extension),
      url: this.fileUrl,
      status: 'pending'
    };

    // Check if file already exists
    if (!this.selectedFiles.some(f => f.url === this.fileUrl)) {
      this.selectedFiles.push(uploadedFile);
      this.fileUrl = '';
      this.errorMessage = '';
    } else {
      this.errorMessage = 'This file URL has already been added.';
    }
  }

  private getMimeTypeFromExtension(extension: string): string {
    switch (extension) {
      case '.xlsx':
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      case '.xls':
        return 'application/vnd.ms-excel';
      case '.pdf':
        return 'application/pdf';
      default:
        return 'application/octet-stream';
    }
  }

  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
    this.errorMessage = '';
  }

  async onUpload(): Promise<void> {
    if (this.selectedFiles.length === 0) {
      this.errorMessage = 'Please select at least one file to upload.';
      return;
    }

    this.isUploading = true;
    this.uploadProgress = 0;
    this.errorMessage = '';

    try {
      const uploadPromises = this.selectedFiles.map(async (file, index) => {
        file.status = 'uploading';
        
        try {
          const result = await this.documentUploadService.uploadFile(file);
          file.status = 'success';
          return result;
        } catch (error) {
          file.status = 'error';
          file.error = error instanceof Error ? error.message : 'Upload failed';
          throw error;
        } finally {
          // Update progress
          this.uploadProgress = Math.round(((index + 1) / this.selectedFiles.length) * 100);
        }
      });

      const results = await Promise.allSettled(uploadPromises);
      const successfulUploads = results
        .filter(result => result.status === 'fulfilled')
        .map(result => (result as PromiseFulfilledResult<any>).value);

      if (successfulUploads.length > 0) {
        this.filesUploaded.emit(successfulUploads);
        this.onClose();
      } else {
        this.errorMessage = 'All file uploads failed. Please try again.';
      }
    } catch (error) {
      this.errorMessage = 'Upload failed. Please try again.';
      console.error('Upload error:', error);
    } finally {
      this.isUploading = false;
    }
  }

  onClose(): void {
    this.resetState();
    this.closeModal.emit();
  }

  onBackdropClick(event: Event): void {
    if (event.target === event.currentTarget) {
      this.onClose();
    }
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  getFileIcon(file: UploadedFile): string {
    if (file.type.includes('pdf')) {
      return 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z';
    } else if (file.type.includes('excel') || file.type.includes('spreadsheet')) {
      return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z';
    }
    return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z';
  }

  getFileIconClass(file: UploadedFile): string {
    if (file.type.includes('pdf')) {
      return 'bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400';
    } else if (file.type.includes('excel') || file.type.includes('spreadsheet')) {
      return 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400';
    }
    return 'bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-400';
  }
}
