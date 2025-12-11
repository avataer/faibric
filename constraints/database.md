# Database Constraints

## Overview
These constraints ensure proper database usage patterns in generated code.

## Rules

### Faibric DB API Usage
- Use the Faibric Database API for all data operations
- Do not use raw SQL queries directly
- Use the provided ORM/query builder patterns
- Handle database errors appropriately

### Query Patterns
- Use pagination for large datasets
- Index frequently queried fields
- Avoid N+1 query problems
- Use transactions for multi-step operations

### Data Validation
- Validate data before saving
- Use appropriate data types
- Enforce constraints at the database level
- Handle null/undefined values

### Security
- Use parameterized queries to prevent SQL injection
- Sanitize input before database operations
- Implement row-level security where needed
- Audit sensitive data access

### Performance
- Use connection pooling
- Cache frequently accessed data
- Optimize query performance
- Use appropriate indexes

### Data Integrity
- Use foreign key constraints
- Implement soft deletes where appropriate
- Maintain data consistency
- Handle concurrent modifications

## Applies To
python, typescript, service, model

## Examples

### Using Faibric DB API
```typescript
// ❌ WRONG - Raw query
const users = await db.query('SELECT * FROM users WHERE active = true');

// ✅ CORRECT - Using Faibric DB API
const users = await faibricDB.collection('users')
  .where('active', '==', true)
  .get();
```

### Pagination Pattern
```typescript
const PAGE_SIZE = 20;

async function getUsers(page: number = 1) {
  return await faibricDB.collection('users')
    .orderBy('created_at', 'desc')
    .limit(PAGE_SIZE)
    .offset((page - 1) * PAGE_SIZE)
    .get();
}
```






