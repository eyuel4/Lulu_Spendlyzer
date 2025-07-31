# 📊 Comprehensive Logging System Guide

## Overview

The Lulu Spendlyzer application now includes a comprehensive database logging system that provides:

- **System Error Logging**: All application errors logged to database with async persistence
- **Audit Trail**: Complete audit logging for user actions and system events
- **Frontend Integration**: Frontend errors automatically sent to backend for logging
- **Rich Metadata**: IP addresses, user agents, session IDs, and request tracing
- **Performance**: Async background processing for high-performance logging

## Architecture

### Database Tables

#### SystemLog Table
```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY,
    level VARCHAR(20) NOT NULL,           -- 'ERROR', 'WARNING', 'INFO', 'DEBUG'
    category VARCHAR(50) NOT NULL,        -- 'AUTH', 'EMAIL', 'DATABASE', 'API', 'SYSTEM'
    source VARCHAR(100) NOT NULL,         -- Component/service name
    title VARCHAR(200) NOT NULL,          -- Error title
    message TEXT NOT NULL,                -- Error message
    error_type VARCHAR(100),              -- Exception class name
    error_details TEXT,                   -- Full error details/stack trace
    user_id INTEGER,                      -- Associated user (if applicable)
    session_id VARCHAR(100),              -- Session identifier
    request_id VARCHAR(100),              -- Request identifier for tracing
    endpoint VARCHAR(200),                -- API endpoint (if applicable)
    method VARCHAR(10),                   -- HTTP method (if applicable)
    ip_address VARCHAR(45),               -- Client IP address
    user_agent VARCHAR(500),              -- User agent string
    environment VARCHAR(20),              -- Environment (dev, staging, prod)
    metadata JSON,                        -- Additional structured data
    tags JSON,                            -- Tags for categorization
    created_at DATETIME NOT NULL,         -- Timestamp
    updated_at DATETIME                   -- Last update timestamp
);
```

#### AuditLog Table
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,      -- 'LOGIN', 'LOGOUT', 'CREATE', 'UPDATE', 'DELETE'
    resource_type VARCHAR(50) NOT NULL,   -- 'USER', 'TRANSACTION', 'CARD', 'REPORT'
    resource_id VARCHAR(100),             -- ID of the affected resource
    user_id INTEGER,                      -- User who performed the action
    performed_by INTEGER,                 -- Who performed the action
    action VARCHAR(200) NOT NULL,         -- Human-readable action description
    details TEXT,                         -- Detailed description
    changes JSON,                         -- Before/after data for updates
    is_successful VARCHAR(10),            -- 'SUCCESS', 'FAILURE', 'PARTIAL'
    failure_reason TEXT,                  -- Reason for failure (if applicable)
    ip_address VARCHAR(45),               -- Client IP address
    user_agent VARCHAR(500),              -- User agent string
    session_id VARCHAR(100),              -- Session identifier
    request_id VARCHAR(100),              -- Request identifier
    metadata JSON,                        -- Additional metadata
    created_at DATETIME NOT NULL          -- Timestamp
);
```

### Backend Components

#### LoggingService (`app/services/logging_service.py`)
- **Async Queue Processing**: Background tasks for high-performance logging
- **Batch Processing**: Processes up to 10 logs at a time for efficiency
- **Error Handling**: Fallback to console logging if database fails
- **Rich Context**: Captures IP, user agent, session, and request data

#### API Routes (`app/routes/logs.py`)
- **GET /logs/system**: Retrieve system logs with filtering
- **GET /logs/audit**: Retrieve audit logs with filtering
- **GET /logs/errors/summary**: Get error summary statistics
- **POST /logs/system**: Create system log entry (frontend integration)
- **POST /logs/audit**: Create audit log entry (frontend integration)

### Frontend Components

#### BackendLoggingService (`spendlyzer-frontend/src/app/services/backend-logging.service.ts`)
- **System Error Logging**: Sends frontend errors to backend
- **Audit Event Logging**: Logs user actions and system events
- **Rich Context**: Captures user ID, session ID, IP address, user agent
- **Error Handling**: Fallback to console if backend logging fails

#### Enhanced NotificationService
- **System Error Integration**: Automatically logs system errors to backend
- **User-Friendly**: Shows user notifications while logging system errors
- **Async Processing**: Non-blocking error logging

## Usage Examples

### Backend System Logging

```python
from app.services.logging_service import logging_service

# Log a system error
await logging_service.log_system_error(
    title="Database Connection Failed",
    message="Failed to connect to database",
    error=exception,
    category="DATABASE",
    source="UserService",
    user_id=123,
    metadata={"attempt": 3, "timeout": 30}
)

# Log a system warning
await logging_service.log_system_warning(
    title="High Memory Usage",
    message="Memory usage exceeded 80%",
    category="SYSTEM",
    source="MonitoringService"
)

# Log an audit event
await logging_service.log_audit_event(
    event_type="UPDATE",
    resource_type="USER",
    action="Updated user profile",
    user_id=123,
    resource_id="user_123",
    details="Changed email address",
    changes={"email": {"old": "old@email.com", "new": "new@email.com"}},
    is_successful="SUCCESS"
)
```

### Frontend System Logging

```typescript
import { BackendLoggingService } from './backend-logging.service';

constructor(private backendLogging: BackendLoggingService) {}

// Log a system error
await this.backendLogging.logSystemError(
  'API Call Failed',
  'Failed to fetch user data',
  error,
  'FRONTEND',
  'UserService'
);

// Log an audit event
await this.backendLogging.logAuditEvent(
  'VIEW',
  'DASHBOARD',
  'Viewed dashboard page',
  'User accessed main dashboard',
  undefined,
  'SUCCESS'
);
```

### API Usage

#### Get System Logs
```bash
GET /logs/system?level=ERROR&category=DATABASE&limit=50
```

#### Get Audit Logs
```bash
GET /logs/audit?event_type=LOGIN&user_id=123&limit=100
```

#### Get Error Summary
```bash
GET /logs/errors/summary?days=7
```

## Configuration

### Environment Variables
```bash
# Required for JWT authentication in logging endpoints
JWT_SECRET=your-secret-key-here

# Database URL (already configured)
DB_URL=sqlite+aiosqlite:///finance.db
```

### Database Initialization
```bash
# Create all tables including logging tables
python -m app.core.init_db
```

## Monitoring and Debugging

### Viewing Logs
1. **System Logs**: Access via `/logs/system` endpoint (superuser only)
2. **Audit Logs**: Access via `/logs/audit` endpoint (superuser only)
3. **Error Summary**: Access via `/logs/errors/summary` endpoint (superuser only)

### Log Analysis
- **Error Patterns**: Filter by category, source, or level
- **User Activity**: Track user actions and system usage
- **Performance**: Monitor system performance through logs
- **Security**: Audit security events and suspicious activity

### Common Queries

#### Recent Errors
```bash
GET /logs/system?level=ERROR&limit=10
```

#### User Activity
```bash
GET /logs/audit?user_id=123&limit=50
```

#### Failed Operations
```bash
GET /logs/audit?is_successful=FAILURE&limit=20
```

## Performance Considerations

### Async Processing
- **Background Queues**: Logs are processed asynchronously
- **Batch Processing**: Multiple logs processed together
- **Non-Blocking**: Logging doesn't block user operations

### Database Optimization
- **Indexes**: Optimized indexes for common queries
- **Partitioning**: Consider partitioning for high-volume logs
- **Retention**: Implement log retention policies

### Monitoring
- **Queue Size**: Monitor logging queue size
- **Processing Time**: Track log processing performance
- **Error Rates**: Monitor logging system errors

## Security

### Access Control
- **Superuser Only**: Log viewing requires superuser privileges
- **Authentication**: All logging endpoints require valid JWT
- **Audit Trail**: All access to logs is itself logged

### Data Protection
- **PII Filtering**: Sensitive data should be filtered from logs
- **Encryption**: Consider encrypting sensitive log data
- **Retention**: Implement appropriate log retention policies

## Troubleshooting

### Common Issues

#### Logs Not Appearing
1. Check if logging service is started
2. Verify database connection
3. Check for logging service errors in console

#### High Memory Usage
1. Monitor logging queue size
2. Check for memory leaks in logging service
3. Consider log retention policies

#### Performance Issues
1. Monitor log processing time
2. Check database performance
3. Consider log aggregation or sampling

### Debug Commands

#### Check Logging Service Status
```python
# In Python console
from app.services.logging_service import logging_service
print(f"Service running: {logging_service._is_running}")
print(f"Queue size: {logging_service._log_queue.qsize()}")
```

#### Manual Log Creation
```python
# Create a test log
await logging_service.log_system_info(
    title="Test Log",
    message="This is a test log entry",
    category="TEST",
    source="Manual"
)
```

## Best Practices

### Logging Guidelines
1. **Be Specific**: Use descriptive titles and messages
2. **Include Context**: Add relevant metadata and tags
3. **Categorize Properly**: Use appropriate categories and sources
4. **Don't Log Sensitive Data**: Avoid logging passwords, tokens, etc.
5. **Use Appropriate Levels**: ERROR, WARNING, INFO, DEBUG

### Performance Guidelines
1. **Async Logging**: Always use async logging methods
2. **Batch Operations**: Group related log entries when possible
3. **Monitor Queue Size**: Keep an eye on logging queue performance
4. **Implement Retention**: Set up log retention policies

### Security Guidelines
1. **Access Control**: Restrict log access to authorized users
2. **Audit Access**: Log all access to log data
3. **Data Protection**: Filter sensitive information from logs
4. **Encryption**: Consider encrypting sensitive log data

## Future Enhancements

### Planned Features
- **Log Aggregation**: Centralized log collection and analysis
- **Real-time Monitoring**: Live log monitoring and alerting
- **Log Analytics**: Advanced log analysis and reporting
- **Integration**: Integration with external monitoring tools
- **Machine Learning**: Automated log analysis and anomaly detection

### Scalability Improvements
- **Distributed Logging**: Support for distributed logging across services
- **Log Streaming**: Real-time log streaming capabilities
- **Advanced Filtering**: More sophisticated log filtering and search
- **Performance Optimization**: Further performance improvements for high-volume logging 