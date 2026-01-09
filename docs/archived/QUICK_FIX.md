# BUG FOUND - Project ID is NaN

The frontend can't read the project ID from the URL.

## The issue:
`/api/projects/NaN/progress/` <- ID is NaN

## Quick test:
After creating a project, manually go to:
http://localhost:5173/create/11

(Replace 11 with the actual project ID shown above)

This will work and show progress!

## The root cause:
The CreateProduct page needs to wait for the response before navigating.
