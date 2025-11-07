from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    success: bool
    fileId: str
    fileName: str
    fileUrl: str
    fileSize: int
    fileType: str
    uploadedAt: str
    message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "fileId": "123e4567-e89b-12d3-a456-426614174000",
                "fileName": "bank_statement.xlsx",
                "fileUrl": "https://s3.amazonaws.com/bucket/documents/123/123e4567-e89b-12d3-a456-426614174000.xlsx",
                "fileSize": 1024000,
                "fileType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "uploadedAt": "2024-01-15T10:30:00Z",
                "message": "File uploaded successfully"
            }
        }


class UploadProgressResponse(BaseModel):
    loaded: int
    total: int
    percentage: float

    class Config:
        json_schema_extra = {
            "example": {
                "loaded": 512000,
                "total": 1024000,
                "percentage": 50.0
            }
        }


class ProcessDocumentResponse(BaseModel):
    success: bool
    transactionCount: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "transactionCount": 25,
                "message": "Document processed successfully"
            }
        }


class ProcessingStatusResponse(BaseModel):
    status: ProcessingStatus
    progress: int = Field(..., ge=0, le=100)
    message: str
    transactionCount: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "progress": 75,
                "message": "Extracting transaction data...",
                "transactionCount": None
            }
        }


class FileValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "error": None
            }
        }


class DocumentMetadata(BaseModel):
    fileId: str
    fileName: str
    fileType: str
    fileSize: int
    uploadedAt: datetime
    processedAt: Optional[datetime] = None
    transactionCount: Optional[int] = None
    status: ProcessingStatus

    class Config:
        json_schema_extra = {
            "example": {
                "fileId": "123e4567-e89b-12d3-a456-426614174000",
                "fileName": "bank_statement.xlsx",
                "fileType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "fileSize": 1024000,
                "uploadedAt": "2024-01-15T10:30:00Z",
                "processedAt": "2024-01-15T10:35:00Z",
                "transactionCount": 25,
                "status": "completed"
            }
        }

