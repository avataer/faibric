# Security Constraints

## Overview
These constraints ensure generated code follows security best practices and avoids common vulnerabilities.

## Rules

### Input Handling
- Always sanitize user input before using it
- Never use `eval()` or `new Function()` with user input
- Validate input types and lengths
- Use parameterized queries for database operations
- Escape output when rendering HTML

### Authentication & Authorization
- Never store passwords in plain text
- Use secure session management
- Implement proper CSRF protection
- Check authorization on every protected endpoint
- Use HTTPS for all sensitive data transmission

### Code Injection Prevention
- Do not use `innerHTML` with unsanitized content
- Avoid `dangerouslySetInnerHTML` in React without sanitization
- Never execute user-provided code
- Use Content Security Policy headers
- Sanitize data before database insertion

### API Security
- Use authentication tokens for API calls
- Implement rate limiting
- Validate all API input
- Do not expose internal errors to users
- Log security events

### Secrets Management
- Never hardcode API keys or passwords
- Use environment variables for secrets
- Do not commit secrets to version control
- Rotate secrets regularly

## Applies To
typescript, javascript, python, api

## Examples

### Bad - Unsafe innerHTML
```javascript
element.innerHTML = userInput; // WRONG
```

### Good - Sanitized
```javascript
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput); // CORRECT
```






