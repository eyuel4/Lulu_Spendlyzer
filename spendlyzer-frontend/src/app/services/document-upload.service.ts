import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpProgressEvent } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface UploadResponse {
  success: boolean;
  fileId: string;
  fileName: string;
  fileUrl: string;
  fileSize: number;
  fileType: string;
  uploadedAt: string;
  message?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

@Injectable({
  providedIn: 'root'
})
export class DocumentUploadService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Upload a file to S3 via backend
   */
  uploadFile(file: { file?: File; url?: string; name: string; type: string }): Observable<UploadResponse> {
    if (file.file) {
      return this.uploadFileFromFile(file.file);
    } else if (file.url) {
      return this.uploadFileFromUrl(file.url, file.name, file.type);
    } else {
      return throwError(() => new Error('No file or URL provided'));
    }
  }

  /**
   * Upload file from File object
   */
  private uploadFileFromFile(file: File): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('fileName', file.name);
    formData.append('fileType', file.type);

    return this.http.post<UploadResponse>(`${this.apiUrl}/upload/document`, formData, {
      reportProgress: true,
      observe: 'events'
    }).pipe(
      map((event: HttpEvent<UploadResponse>) => {
        if (event.type === HttpEventType.Response) {
          return event.body!;
        }
        throw new Error('Upload failed');
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Upload file from URL
   */
  private uploadFileFromUrl(url: string, fileName: string, fileType: string): Observable<UploadResponse> {
    const payload = {
      fileUrl: url,
      fileName: fileName,
      fileType: fileType
    };

    return this.http.post<UploadResponse>(`${this.apiUrl}/upload/document-from-url`, payload).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get upload progress for a file
   */
  getUploadProgress(fileId: string): Observable<UploadProgress> {
    return this.http.get<UploadProgress>(`${this.apiUrl}/upload/progress/${fileId}`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get list of uploaded files for current user
   */
  getUploadedFiles(): Observable<UploadResponse[]> {
    return this.http.get<UploadResponse[]>(`${this.apiUrl}/upload/files`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete an uploaded file
   */
  deleteFile(fileId: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(`${this.apiUrl}/upload/files/${fileId}`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Process uploaded document for transaction extraction
   */
  processDocument(fileId: string): Observable<{ success: boolean; transactionCount: number; message: string }> {
    return this.http.post<{ success: boolean; transactionCount: number; message: string }>(
      `${this.apiUrl}/upload/process/${fileId}`,
      {}
    ).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get processing status for a document
   */
  getProcessingStatus(fileId: string): Observable<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    message: string;
    transactionCount?: number;
  }> {
    return this.http.get<{
      status: 'pending' | 'processing' | 'completed' | 'failed';
      progress: number;
      message: string;
      transactionCount?: number;
    }>(`${this.apiUrl}/upload/process-status/${fileId}`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    // Check file type
    const allowedTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
      'application/vnd.ms-excel', // .xls
      'application/pdf' // .pdf
    ];

    const allowedExtensions = ['.xlsx', '.xls', '.pdf'];
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));

    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(extension)) {
      return {
        valid: false,
        error: 'Only Excel (.xlsx, .xls) and PDF (.pdf) files are allowed.'
      };
    }

    // Check file size (max 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return {
        valid: false,
        error: 'File size must be less than 10MB.'
      };
    }

    return { valid: true };
  }

  /**
   * Validate URL
   */
  validateUrl(url: string): { valid: boolean; error?: string } {
    try {
      new URL(url);
    } catch {
      return {
        valid: false,
        error: 'Please enter a valid URL.'
      };
    }

    const allowedExtensions = ['.xlsx', '.xls', '.pdf'];
    const urlParts = url.split('/');
    const filename = urlParts[urlParts.length - 1];
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));

    if (!allowedExtensions.includes(extension)) {
      return {
        valid: false,
        error: 'URL must point to an Excel (.xlsx, .xls) or PDF (.pdf) file.'
      };
    }

    return { valid: true };
  }

  private handleError(error: any): Observable<never> {
    let errorMessage = 'An error occurred during upload';
    
    if (error.error?.message) {
      errorMessage = error.error.message;
    } else if (error.message) {
      errorMessage = error.message;
    } else if (error.status === 413) {
      errorMessage = 'File too large. Maximum size is 10MB.';
    } else if (error.status === 415) {
      errorMessage = 'Unsupported file type. Only Excel and PDF files are allowed.';
    } else if (error.status === 0) {
      errorMessage = 'Network error. Please check your connection.';
    }

    console.error('Document upload error:', error);
    return throwError(() => new Error(errorMessage));
  }
}

