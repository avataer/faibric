# Styling Constraints

## Overview
These constraints ensure consistent and maintainable styling across generated code.

## Rules

### CSS Variables
- Use CSS custom properties for colors, spacing, and typography
- Define variables at the root level
- Use semantic variable names (e.g., `--color-primary`, not `--blue`)

### Layout
- Use Flexbox or CSS Grid for layouts
- Avoid fixed widths where possible
- Make components responsive by default
- Use relative units (rem, em, %) over fixed units (px)

### Color Theme
- Support both light and dark themes
- Use appropriate contrast ratios (WCAG AA minimum)
- Define a consistent color palette
- Use opacity for hover/active states

### Typography
- Use a consistent font stack
- Define a type scale for headings
- Use line-height of 1.5 for body text
- Limit line length for readability (60-80 characters)

### Component Styling
- Keep styles scoped to components
- Use meaningful class names
- Avoid deep nesting (max 3 levels)
- Prefer composition over inheritance

### Animations
- Use CSS transitions for simple animations
- Keep animations under 300ms for UI feedback
- Respect `prefers-reduced-motion`
- Use GPU-accelerated properties (transform, opacity)

## Applies To
css, html, typescript, javascript, component

## Examples

### CSS Variables
```css
:root {
  --color-primary: #3B82F6;
  --color-secondary: #6366F1;
  --spacing-unit: 0.5rem;
  --font-sans: 'Inter', system-ui, sans-serif;
}
```






