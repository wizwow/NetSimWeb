Write-Host "Building NetSim-Flow..." -ForegroundColor Green
pnpm build
Write-Host "Starting NetSim-Flow in Production Mode..." -ForegroundColor Green
pnpm start:prod
