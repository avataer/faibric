# API Usage Constraints

## Overview
These constraints ensure proper API usage patterns in generated code.

## Rules

### Gateway Usage
- Use the Faibric API Gateway for all external API calls
- Do not make direct calls to external APIs
- Route all requests through `/api/gateway/`
- Register external APIs in the gateway configuration

### Error Handling
- Always handle API errors gracefully
- Show user-friendly error messages
- Log errors for debugging
- Implement retry logic for transient failures

### Authentication
- Include authentication headers on protected endpoints
- Handle token expiration and refresh
- Use secure storage for tokens
- Clear tokens on logout

### Request Patterns
- Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- Include proper content-type headers
- Handle loading states
- Cancel requests on component unmount

### Response Handling
- Validate response data
- Handle empty/null responses
- Transform data as needed
- Cache responses when appropriate

### Rate Limiting
- Respect API rate limits
- Implement client-side throttling for user actions
- Queue bulk operations
- Show feedback during long operations

## Applies To
typescript, javascript, service, api

## Examples

### Using Gateway for External API
```typescript
// ❌ WRONG - Direct external call
const data = await fetch('https://external-api.com/data');

// ✅ CORRECT - Through gateway
const data = await fetch('/api/gateway/external-api/', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});
```

### Error Handling Pattern
```typescript
try {
  const response = await apiClient.get('/endpoint');
  return response.data;
} catch (error) {
  if (error.response?.status === 401) {
    // Handle unauthorized
    await refreshToken();
  } else if (error.response?.status === 429) {
    // Handle rate limit
    await delay(error.response.headers['retry-after']);
  } else {
    // Log and show user-friendly error
    console.error('API Error:', error);
    throw new Error('Something went wrong. Please try again.');
  }
}
```






