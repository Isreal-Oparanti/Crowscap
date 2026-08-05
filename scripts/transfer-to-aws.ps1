# Transfer Crowscap Backend to AWS EC2
# Run this PowerShell script on your local Windows machine

$AWS_IP = "54.160.242.246"
$SSH_KEY = "$env:USERPROFILE\Downloads\crowscap-aws.pem"
$PROJECT_ROOT = $PSScriptRoot
$BACKEND_DIR = Join-Path $PROJECT_ROOT "backend"

Write-Host "🚀 Transferring Crowscap backend to AWS..." -ForegroundColor Green
Write-Host "Target: $AWS_IP" -ForegroundColor Yellow
Write-Host "Key: $SSH_KEY" -ForegroundColor Yellow
Write-Host ""

# Check SSH key exists
if (-not (Test-Path $SSH_KEY)) {
    Write-Host "❌ SSH key not found at: $SSH_KEY" -ForegroundColor Red
    Write-Host "Please ensure crowscap-aws.pem is in your Downloads folder." -ForegroundColor Yellow
    exit 1
}

# Create temporary directory for filtering
$tempDir = Join-Path $env:TEMP "crowscap-transfer-$(Get-Random)"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

Write-Host "📦 Preparing files..." -ForegroundColor Cyan

# Copy backend directory excluding large/unneeded files
Get-ChildItem -Path $BACKEND_DIR -Recurse -File | Where-Object {
    $path = $_.FullName -replace [regex]::Escape($BACKEND_DIR), ""
    # Exclude these patterns
    -not ($path -match "^\.venv" -or 
          $path -match "__pycache__" -or 
          $path -match "\.db$" -or 
          $path -match "\.pytest_cache" -or 
          $path -match "node_modules" -or
          $path -match "build$" -or
          $path -match "dist$")
} | ForEach-Object {
    $destPath = Join-Path $tempDir ($_.FullName -replace [regex]::Escape($BACKEND_DIR), "")
    $destFolder = Split-Path $destPath -Parent
    if (-not (Test-Path $destFolder)) { New-Item -ItemType Directory -Force -Path $destFolder | Out-Null }
    Copy-Item $_.FullName -Destination $destPath -Force
}

Copy-Item -Path $PROJECT_ROOT -Include "*.sh", "*.md", "*.service", "*.conf" -Recurse -Destination $tempDir -Force

Write-Host "📤 Transferring to AWS via SCP..." -ForegroundColor Cyan

# Use pscp (PuTTY) or ssh/scp if available
$scpExe = Get-Command pscp -ErrorAction SilentlyContinue
if ($scpExe) {
    # Use PuTTY PSCP
    & $scpExe.Source -r -pw "" `
        (Join-Path $tempDir "*") `
        "ec2-user@$AWS_IP:/home/ec2-user/crowscap-backend/"
} else {
    # Try WSL or Git bash scp
    Write-Host "⚠️ Using SCP from Git Bash..." -ForegroundColor Yellow
    
    $scpArgs = @("-r", "-i", "`"$SSH_KEY`"", "--exclude=.venv", "--exclude=__pycache__", 
                 "--exclude='*.db'", "--exclude=.pytest_cache", "--exclude=node_modules",
                 "$BACKEND_DIR/", "ec2-user@$AWS_IP:/home/ec2-user/")
    
    & "scp.exe" $scpArgs 2>&1 | ForEach-Object { Write-Host $_ }
}

# Transfer config files
Write-Host "📄 Transferring config files..." -ForegroundColor Cyan
scp -i "$SSH_KEY" "$PROJECT_ROOT\quick-setup.sh" "ec2-user@$AWS_IP:~/"
scp -i "$SSH_KEY" "$PROJECT_ROOT\crowscap.service" "ec2-user@$AWS_IP:~/"
scp -i "$SSH_KEY" "$PROJECT_ROOT\nginx-crowscap.conf" "ec2-user@$AWS_IP:~/"
scp -i "$SSH_KEY" "$PROJECT_ROOT\.env.production" "ec2-user@$AWS_IP:~/"

# Cleanup temp
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ Transfer complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH into AWS: ssh -i $SSH_KEY ec2-user@$AWS_IP"
Write-Host "2. Run setup: ./quick-setup.sh"
Write-Host "3. Edit .env.production with your secrets"
Write-Host "4. Start service: sudo systemctl start crowscap"
Write-Host ""
