pwsh ./scripts/setup-node.ps1
cd backend/frontend
npm ci || npm install
npm run typecheck
npm run build
