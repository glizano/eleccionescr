# Security Policy

## Supported Versions

We actively support the following versions of EleccionesCR with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

We take the security of EleccionesCR seriously. If you believe you have found a security vulnerability, please report it to us responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. **DO** send a detailed report to the maintainers via:
   - GitHub Security Advisories (preferred): Go to the Security tab and click "Report a vulnerability"
   - Email: [Contact information to be added]

### What to Include

Please include the following information in your report:

- Type of vulnerability (e.g., XSS, SQL injection, authentication bypass)
- Full path of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability and potential attack scenarios

### Response Timeline

- **Initial Response**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Status Update**: We will provide a more detailed response within 7 days, including next steps
- **Fix Timeline**: We aim to release a fix within 30 days for critical vulnerabilities
- **Disclosure**: We follow coordinated disclosure practices and will work with you on timing

### Security Best Practices for Deployment

When deploying EleccionesCR, follow these security guidelines:

#### Environment Variables
- Never commit `.env` files to version control
- Use strong, unique API keys for production
- Rotate API keys periodically
- Use secrets management systems in production (e.g., AWS Secrets Manager, HashiCorp Vault)

#### Network Security
- Run behind a reverse proxy (nginx, Cloudflare) with SSL/TLS
- Restrict CORS origins in production (don't use `CORS_ORIGINS=*`)
- Use private networks for internal services (Qdrant, Langfuse DB)
- Enable firewall rules to restrict access

#### Application Security
- Keep all dependencies up to date
- Review security advisories for dependencies regularly
- Use `GOOGLE_SAFETY_THRESHOLD=BLOCK_MEDIUM_AND_ABOVE` or higher
- Enable rate limiting in production
- Monitor logs for suspicious activity

#### Docker Security
- Don't run containers as root in production
- Use specific image versions (avoid `latest` tag)
- Scan images for vulnerabilities regularly
- Remove development volumes in production builds
- Use Docker secrets for sensitive data

#### Database Security
- Change default Qdrant and Langfuse credentials
- Use API keys for Qdrant in production
- Enable authentication on all database services
- Regular backups with encryption

## Known Security Considerations

### Current Limitations

1. **Rate Limiting**: Basic rate limiting is configured but may need adjustment based on your deployment scale
2. **Input Validation**: User inputs are validated for length and format, but additional sanitization may be needed for specific use cases
3. **Authentication**: The current version doesn't include built-in user authentication - implement this at the infrastructure level if needed

### Security Features

- ✅ Input validation on API endpoints
- ✅ Security headers in nginx configuration
- ✅ API key validation at startup
- ✅ Configurable CORS policies
- ✅ LLM safety filters (Google Gemini)
- ✅ No secrets in source code
- ✅ Dependency vulnerability scanning in CI

## Security Updates

Security updates will be released as patch versions (e.g., 2.0.1 → 2.0.2) and announced via:
- GitHub Security Advisories
- GitHub Releases with changelog
- Repository README

## Bug Bounty Program

We currently do not have a bug bounty program, but we deeply appreciate security researchers who help us maintain the security of EleccionesCR and will publicly acknowledge your contribution (with your permission).

## Questions

If you have questions about this security policy, please open a GitHub Discussion in the Security category or contact the maintainers.

---

Last updated: December 2024
