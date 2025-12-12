# React Constraints

## Overview
These constraints ensure generated React code follows modern patterns and best practices.

## Rules

### Components
- Use functional components with hooks only
- Do not use class components
- Keep components small and focused (single responsibility)
- Extract reusable logic into custom hooks

### Hooks
- Follow the rules of hooks (only at top level, only in React functions)
- Use `useMemo` and `useCallback` for expensive computations
- Prefer `useReducer` for complex state logic
- Clean up effects properly

### State Management
- Keep state as local as possible
- Lift state up only when necessary
- Use context for truly global state
- Consider state machines for complex flows

### Props
- Define prop types with TypeScript interfaces
- Use destructuring for props
- Provide sensible default values
- Document complex props

### Performance
- Memoize expensive components with `React.memo`
- Use virtualization for long lists
- Lazy load heavy components
- Avoid inline object/array creation in render

### Event Handlers
- Name handlers with `handle` prefix (e.g., `handleClick`)
- Use the proper event types
- Debounce expensive handlers
- Prevent default where appropriate

### Accessibility
- Use semantic HTML elements
- Include proper ARIA attributes
- Ensure keyboard navigation
- Provide meaningful alt text

## Applies To
typescript, javascript, component, hook

## Examples

### Good Component Structure
```typescript
interface UserCardProps {
  user: User;
  onEdit?: () => void;
}

export const UserCard: React.FC<UserCardProps> = ({ user, onEdit }) => {
  const handleEditClick = useCallback(() => {
    onEdit?.();
  }, [onEdit]);

  return (
    <article className="user-card">
      <h2>{user.name}</h2>
      <button onClick={handleEditClick}>Edit</button>
    </article>
  );
};
```









