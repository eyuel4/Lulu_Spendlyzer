from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import boto3
import uuid
import os
import mimetypes
from datetime import datetime
import asyncio
from botocore.exceptions import ClientError, NoCredentialsError
import logging

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..models.transaction import Transaction
from ..models.system_log import SystemLog
from ..services.logging_service import LoggingService
from ..schemas.upload import (
    UploadResponse, 
    UploadProgressResponse, 
    ProcessDocumentResponse,
    ProcessingStatusResponse
)

router = APIRouter(prefix="/upload", tags=["upload"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "spendlyzer-documents")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize S3 client
try:
    s3_client = boto3.client(
        's3',
        region_name=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
except NoCredentialsError:
    logger.warning("AWS credentials not found. S3 uploads will be disabled.")
    s3_client = None

# Allowed file types
ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',  # .xls
    'application/pdf'  # .pdf
]

ALLOWED_EXTENSIONS = ['.xlsx', '.xls', '.pdf']

# File size limit (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# In-memory storage for upload progress (in production, use Redis)
upload_progress = {}
processing_status = {}


def validate_file_type(filename: str, content_type: str) -> bool:
    """Validate if file type is allowed"""
    # Check by MIME type
    if content_type in ALLOWED_MIME_TYPES:
        return True
    
    # Check by file extension
    extension = os.path.splitext(filename)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def generate_s3_key(user_id: int, filename: str) -> str:
    """Generate unique S3 key for file"""
    file_id = str(uuid.uuid4())
    extension = os.path.splitext(filename)[1]
    return f"documents/{user_id}/{file_id}{extension}"


async def upload_to_s3(file_content: bytes, s3_key: str, content_type: str) -> str:
    """Upload file to S3 and return URL"""
    if not s3_client:
        raise HTTPException(status_code=503, detail="S3 service not configured")
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            ServerSideEncryption='AES256'
        )
        
        # Generate presigned URL for access
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600  # 1 hour
        )
        
        return url
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to S3")


async def download_file_from_url(url: str) -> tuple[bytes, str]:
    """Download file from URL and return content and filename"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Failed to download file from URL")
                
                content = await response.read()
                filename = url.split('/')[-1]
                
                # Validate file size
                if len(content) > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File too large")
                
                return content, filename
    except Exception as e:
        logger.error(f"Error downloading file from URL: {e}")
        raise HTTPException(status_code=400, detail="Failed to download file from URL")


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fileName: str = Form(...),
    fileType: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document file to S3"""
    try:
        # Validate file type
        if not validate_file_type(fileName, fileType):
            raise HTTPException(
                status_code=415, 
                detail="Unsupported file type. Only Excel (.xlsx, .xls) and PDF (.pdf) files are allowed."
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
        # Generate S3 key
        s3_key = generate_s3_key(current_user.id, fileName)
        
        # Upload to S3
        file_url = await upload_to_s3(file_content, s3_key, fileType)
        
        # Generate file ID
        file_id = str(uuid.uuid4())
        
        # Log the upload
        background_tasks.add_task(
            LoggingService.log_system_event,
            db=db,
            user_id=current_user.id,
            event_type="document_upload",
            details={
                "file_id": file_id,
                "filename": fileName,
                "file_size": len(file_content),
                "file_type": fileType,
                "s3_key": s3_key
            }
        )
        
        return UploadResponse(
            success=True,
            fileId=file_id,
            fileName=fileName,
            fileUrl=file_url,
            fileSize=len(file_content),
            fileType=fileType,
            uploadedAt=datetime.utcnow().isoformat(),
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@router.post("/document-from-url", response_model=UploadResponse)
async def upload_document_from_url(
    background_tasks: BackgroundTasks,
    fileUrl: str = Form(...),
    fileName: str = Form(...),
    fileType: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document from URL to S3"""
    try:
        # Validate file type
        if not validate_file_type(fileName, fileType):
            raise HTTPException(
                status_code=415, 
                detail="Unsupported file type. Only Excel (.xlsx, .xls) and PDF (.pdf) files are allowed."
            )
        
        # Download file from URL
        file_content, downloaded_filename = await download_file_from_url(fileUrl)
        
        # Use original filename if provided, otherwise use downloaded filename
        final_filename = fileName if fileName else downloaded_filename
        
        # Generate S3 key
        s3_key = generate_s3_key(current_user.id, final_filename)
        
        # Upload to S3
        file_url = await upload_to_s3(file_content, s3_key, fileType)
        
        # Generate file ID
        file_id = str(uuid.uuid4())
        
        # Log the upload
        background_tasks.add_task(
            LoggingService.log_system_event,
            db=db,
            user_id=current_user.id,
            event_type="document_upload_from_url",
            details={
                "file_id": file_id,
                "filename": final_filename,
                "file_size": len(file_content),
                "file_type": fileType,
                "source_url": fileUrl,
                "s3_key": s3_key
            }
        )
        
        return UploadResponse(
            success=True,
            fileId=file_id,
            fileName=final_filename,
            fileUrl=file_url,
            fileSize=len(file_content),
            fileType=fileType,
            uploadedAt=datetime.utcnow().isoformat(),
            message="File uploaded successfully from URL"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload from URL error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during upload")


@router.get("/progress/{file_id}", response_model=UploadProgressResponse)
async def get_upload_progress(file_id: str):
    """Get upload progress for a file"""
    if file_id not in upload_progress:
        raise HTTPException(status_code=404, detail="File not found")
    
    return upload_progress[file_id]


@router.get("/files", response_model=List[UploadResponse])
async def get_uploaded_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of uploaded files for current user"""
    # In a real implementation, you would store file metadata in database
    # For now, return empty list
    return []


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an uploaded file"""
    try:
        # In a real implementation, you would:
        # 1. Get file metadata from database
        # 2. Delete from S3
        # 3. Remove from database
        
        # Log the deletion
        background_tasks.add_task(
            LoggingService.log_system_event,
            db=db,
            user_id=current_user.id,
            event_type="document_delete",
            details={"file_id": file_id}
        )
        
        return {"success": True, "message": "File deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during deletion")


@router.post("/process/{file_id}", response_model=ProcessDocumentResponse)
async def process_document(
    file_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process uploaded document for transaction extraction"""
    try:
        # Initialize processing status
        processing_status[file_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting document processing...",
            "transactionCount": 0
        }
        
        # Start background processing
        background_tasks.add_task(
            process_document_background,
            file_id=file_id,
            user_id=current_user.id,
            db=db
        )
        
        return ProcessDocumentResponse(
            success=True,
            transactionCount=0,
            message="Document processing started"
        )
        
    except Exception as e:
        logger.error(f"Process document error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during processing")


@router.get("/process-status/{file_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(file_id: str):
    """Get processing status for a document"""
    if file_id not in processing_status:
        raise HTTPException(status_code=404, detail="Processing status not found")
    
    return processing_status[file_id]


async def process_document_background(file_id: str, user_id: int, db: Session):
    """Background task to process document"""
    try:
        # Simulate document processing
        # In a real implementation, you would:
        # 1. Download file from S3
        # 2. Parse Excel/PDF content
        # 3. Extract transaction data
        # 4. Save transactions to database
        
        processing_status[file_id]["progress"] = 25
        processing_status[file_id]["message"] = "Downloading file from S3..."
        await asyncio.sleep(1)
        
        processing_status[file_id]["progress"] = 50
        processing_status[file_id]["message"] = "Parsing document content..."
        await asyncio.sleep(1)
        
        processing_status[file_id]["progress"] = 75
        processing_status[file_id]["message"] = "Extracting transaction data..."
        await asyncio.sleep(1)
        
        processing_status[file_id]["progress"] = 100
        processing_status[file_id]["status"] = "completed"
        processing_status[file_id]["message"] = "Document processed successfully"
        processing_status[file_id]["transactionCount"] = 0  # Would be actual count
        
        # Log completion
        LoggingService.log_system_event(
            db=db,
            user_id=user_id,
            event_type="document_processed",
            details={
                "file_id": file_id,
                "transaction_count": 0
            }
        )
        
    except Exception as e:
        logger.error(f"Background processing error: {e}")
        processing_status[file_id]["status"] = "failed"
        processing_status[file_id]["message"] = f"Processing failed: {str(e)}"

