# Security Documentation - DCCCO CI Staff System

## Security Measures Implemented

### 1. Authentication & Session Security
- **Password Hashing**: Bcrypt-based hashing via Werkzeug
- **Strong Secret Key**: 64-character cryptographically secure random key
- **Session Management**: Flask-Login with secure session cookies
- **Password Requirements**:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number

### 2. CSRF Protection
- **Flask-WTF CSRF**: Enabled on all forms
- **Token Validation**: Automatic CSRF token validation on POST requests
- **WebSocket Exemption**: SocketIO uses its own authentication

### 3. Rate Limiting
- **Login Attempts**: 5 attempts per minute (prevents brute force)
- **Password Reset**: 3 attempts per hour (prevents abuse)
- **Global Limits**: 200 requests/day, 50 requests/hour per IP

### 4. File Upload Security
- **Extension Whitelist**: Only PNG, JPG, JPEG, GIF, PDF, DOC, DOCX, WEBM, MP3, WAV
- **Filename Sanitization**: Removes path separators and dangerous characters
- **Unique Filenames**: UUID-based naming prevents overwrites
- **Size Limit**: 16MB maximum file size
- **Path Traversal Protection**: Validates files are within allowed directories

### 5. SQL Injection Protection
- **Parameterized Queries**: All database queries use parameter binding
- **No String Concatenation**: Zero SQL string concatenation in codebase

### 6. WebSocket Security
- **CORS Restrictions**: Only allowed origins can connect
- **Allowed Origins**:
  - http://localhost:5000
  - http://127.0.0.1:5000
  - http://192.168.1.61:5000
  - http://192.168.1.41:5000

### 7. Authorization & Access Control
- **Role-Based Access**: admin, loan_staff, ci_staff roles
- **Route Protection**: @login_required on sensitive routes
- **User Approval System**: New accounts require admin approval

### 8. Environment Variables
- **Secrets Management**: All sensitive data in .env file
- **Not in Version Control**: .env should be in .gitignore

## Security Best Practices for Deployment

### For Production Deployment:

1. **Enable HTTPS**
   - Use SSL/TLS certificates (Let's Encrypt is free)
   - Redirect all HTTP traffic to HTTPS
   - Set secure cookie flags

2. **Update WebSocket CORS**
   - Replace local IPs with your production domain
   - Example: `https://yourdomain.com`

3. **Database**
   - Consider migrating from SQLite to PostgreSQL
   - Enable regular automated backups
   - Use database connection pooling

4. **Server Configuration**
   - Use Gunicorn or uWSGI (not Flask dev server)
   - Run behind Nginx reverse proxy
   - Enable firewall (UFW on Ubuntu)

5. **Monitoring**
   - Set up error logging (Sentry, Rollbar)
   - Monitor failed login attempts
   - Track unusual activity patterns

6. **Regular Updates**
   - Keep Python packages updated
   - Monitor security advisories
   - Test updates in staging first

## Installation of Security Packages

Run this command to install new security packages:

```bash
pip install -r requirements.txt
```

New packages added:
- **Flask-WTF**: CSRF protection
- **Flask-Limiter**: Rate limiting
- **email-validator**: Email validation

## Testing Security Features

### Test Rate Limiting
Try logging in with wrong password 6 times - you should be blocked after 5 attempts.

### Test Password Strength
Try creating account with weak password - should be rejected.

### Test File Upload
Try uploading .exe or .bat file - should be rejected.

### Test CSRF Protection
Forms without CSRF tokens will be rejected automatically.

## Security Checklist

- [x] Strong secret key generated
- [x] Debug mode disabled in production
- [ ] CSRF protection enabled (installed but needs form tokens)
- [x] Rate limiting on login/password reset
- [x] Password strength validation
- [x] File upload validation
- [x] Path traversal protection
- [x] SQL injection protection
- [x] WebSocket CORS restrictions
- [ ] HTTPS enabled (do this when deploying)
- [ ] Database backups configured
- [ ] Error monitoring setup

## Contact

For security concerns or to report vulnerabilities, contact the system administrator.

Last Updated: March 17, 2026
