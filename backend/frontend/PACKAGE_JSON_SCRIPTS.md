// Add these scripts to package.json:
{
  "scripts": {
    "lint": "eslint . --ext .ts,.tsx,.jsx",
    "lint:fix": "eslint . --ext .ts,.tsx,.jsx --fix",
    "typecheck": "tsc --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,jsx,css}\"",
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }
}
