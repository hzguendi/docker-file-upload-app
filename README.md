# Docker File Upload App

A simple, secure Docker container for uploading and downloading files via HTTP for machines with restricted access.

![Dashboard Screenshot](docs/images/dashboard.png)

## 🚀 Features

### Core Features
- **User Authentication**: Secure login with role-based access control
- **File Upload**: Simple drag-and-drop interface for uploading files
- **File Download**: Browse and download previously uploaded files
- **User Roles**: Admin, Writer (upload only), Reader (download only)
- **API Access**: Programmatic file uploads via REST API
- **Security**: Password authentication, HTTPS, rate limiting

### Configuration Options
- Customizable file size limits
- File extension filtering (whitelist/blacklist)
- Custom file naming patterns
- IP address whitelisting
- Extensive logging

## 📋 Prerequisites

- Docker and Docker Compose installed
- Basic familiarity with Docker concepts
- A machine with HTTP/HTTPS access

## 🔧 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/docker-file-upload.git
cd docker-file-upload
```

### 2. Configure SSL (Recommended)

```bash
mkdir -p config/ssl
openssl req -x509 -newkey rsa:4096 -keyout config/ssl/key.pem -out config/ssl/cert.pem -days 365 -nodes
```

### 3. Update Configuration

Edit the default configuration files in the `config` directory:

- `config/config.yml`: Main application settings
- `config/users.yml`: User accounts and roles
- `config/ip_whitelist.yml`: IP access control

### 4. Launch the Container

```bash
docker-compose up -d
```

### 5. Access the Application

- **Web Interface**: http://your-server-ip:8000 (or https://your-server-ip:8443 for HTTPS)
- Default login:
  - Username: `admin`
  - Password: `admin`

## 👥 User Roles

The application supports three user roles:

| Role | Permissions |
|------|-------------|
| **Admin** | Full access - can upload and download files |
| **Writer** | Can only upload files |
| **Reader** | Can only download files |

## 🔐 Security Recommendations

1. **Change Default Passwords**: Update all default passwords in `config/users.yml`
2. **Enable HTTPS**: Always use SSL in production environments
3. **Enable IP Whitelisting**: Restrict access to trusted IP addresses
4. **Set Restrictive File Types**: Use blacklist/whitelist to control allowed file types

## 📥 API Usage

Upload files programmatically using the API endpoint:

```bash
# Upload a file using curl
curl -X POST -u username:password -F "file=@/path/to/yourfile.txt" https://your-server-ip:8443/api/upload
```

## 📁 Directory Structure

```
docker-file-upload/
├── app/                # Application code
├── config/             # Configuration files
│   ├── config.yml      # Main configuration
│   ├── users.yml       # User accounts
│   ├── ip_whitelist.yml # IP access control
│   └── ssl/            # SSL certificates
├── uploads/            # Uploaded files storage
├── logs/               # Application logs
└── docker-compose.yml  # Docker configuration
```

## 🔄 Upgrading

When upgrading from version 1.x to 2.x:

1. Backup your configuration files and uploaded data
2. Pull the latest version
3. Update your configuration files to match the new format
4. Restart the container

## 🔍 Troubleshooting

### Common Issues

1. **Login Issues**: Verify credentials in `config/users.yml`
2. **Permission Denied**: Check user roles and IP whitelist settings
3. **Upload Failures**: Check file size limits and disk space

### Checking Logs

```bash
# View container logs
docker-compose logs

# View application logs
cat logs/server.log
```

## 🛠️ Development

To build and run the application locally:

```bash
# Build the Docker image
docker-compose build

# Run with debug logging
docker-compose up
```

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.