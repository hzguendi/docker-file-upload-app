# Docker File Upload App

A simple, secure Docker container for uploading files via HTTP to machines with restricted access.

## Features

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

## Future Features

- File scanning/virus checking
- Automated file cleanup/retention policies
- Separate authentication for viewing vs uploading
- Download functionality with access controls
- Multi-user support with different permissions

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed on your system
- Basic understanding of Docker and networking

### Quick Start

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/secure-file-upload.git
   cd secure-file-upload
   ```

2. Create SSL certificates for HTTPS:
   ```
   mkdir -p config/ssl
   openssl req -x509 -newkey rsa:4096 -keyout config/ssl/key.pem -out config/ssl/cert.pem -days 365 -nodes
   ```

3. Update the configuration files:
   - `config/config.yml`: Main configuration file
   - `config/passwords.yml`: User passwords (default: admin/admin)
   - `config/ip_whitelist.yml`: IP whitelisting configuration

4. Build and start the container:
   ```
   docker-compose up -d
   ```

5. Access the upload interface:
   - HTTP: `http://your-server-ip:8000`
   - HTTPS: `https://your-server-ip:8443`

## Configuration

### Main Configuration (config.yml)

```yaml
server:
  host: 0.0.0.0
  port: 8000
  ssl:
    enabled: true
    port: 8443
    cert_path: config/ssl/cert.pem
    key_path: config/ssl/key.pem

upload:
  max_size: 100  # Max upload size in MB
  directory: uploads
  whitelist_extensions: []  # Empty list means all are allowed
  blacklist_extensions: ['.exe', '.bat', '.sh', '.php', '.dll', '.bin']
  naming_format: "{timestamp}_{uuid}_{original}"

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: logs/server.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  rotation: true
  max_size_mb: 10
  backup_count: 5

security:
  secret_key: "CHANGE_THIS_TO_A_RANDOM_STRING_IN_PRODUCTION"
  token_expire_minutes: 60
  passwords_file: config/passwords.yml
  ip_whitelist_file: config/ip_whitelist.yml

rate_limit:
  enabled: true
  max_uploads: 10
  window_minutes: 5
```

### Passwords Configuration (passwords.yml)

```yaml
# Default password: "admin" (change in production!)
users:
  - username: admin
    password_hash: "$2b$12$tRIEiVQDQDzWiLa2S3uME.9mDQMJsVQzWya5T0D9v7vY4x1MDJrBK"
```

To generate a new password hash:

```python
import bcrypt
password = "your_new_password"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(hashed.decode())
```

### IP Whitelist Configuration (ip_whitelist.yml)

```yaml
enabled: false  # Set to true to enable IP whitelist

whitelist:
  - 127.0.0.1
  - 192.168.1.*
  - 10.0.0.*
```

## API Usage

To upload files programmatically, use the `/api/upload` endpoint with HTTP Basic Authentication:

```bash
curl -X POST -u admin:admin -F "file=@/path/to/yourfile.txt" http://your-server-ip:8000/api/upload
```

## Security Considerations

1. **Change default passwords**: Update the passwords.yml file with new bcrypt hashes.
2. **Use HTTPS**: Enable SSL in the config and use valid certificates.
3. **IP Whitelisting**: Enable and configure IP whitelisting in production.
4. **Rate limiting**: Adjust rate limits based on your needs and environment.
5. **File type restrictions**: Configure blacklisted extensions appropriately.

## Troubleshooting

### Logs

Logs are stored in the `logs` directory. Check these for debugging information.

### Common Issues

1. **Upload fails with 413 error**: Increase the max_size in config.yml.
2. **Cannot access the server**: Check firewall settings and port forwarding.
3. **SSL certificate issues**: Generate new certificates or use a valid CA-signed certificate.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
