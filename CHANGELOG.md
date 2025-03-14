# Changelog

All notable changes to the Docker File Upload App will be documented in this file.

## [2.0.0] - 2025-03-14

### Added
- User authentication system with login page
- Session management with secure cookies
- Logout functionality
- File download page with listing of uploaded files
- User role system:
  - Reader: Can only access the download page
  - Writer: Can only access the upload page
  - Admin: Full access to both upload and download pages
- User management in config files
- Extended logging for authentication events
- Navigation bar with role-based visibility

### Changed
- Improved UI with modern responsive design
- Enhanced error handling and user feedback
- Updated configuration structure for user roles
- More comprehensive README with examples and screenshots

### Security
- Implemented proper session management
- Added CSRF protection for all forms
- Improved password hashing with stronger algorithms
- Session timeout and secure cookie settings

## [1.0.0] - 2025-03-13

### Initial Release
- Single-page web interface for file uploads
- API endpoint for programmatic uploads
- Configurable upload size limits
- File extension whitelist/blacklist
- Custom file naming patterns
- Extensive logging for debugging and traceability
- Password-based authentication with bcrypt hashing
- HTTPS support with configurable certificates
- Rate limiting to prevent abuse
- IP address whitelisting
- Disk space monitoring
- Drag-and-drop file upload support