# copy_to_usb.ps1 <USB_DRIVE_LETTER> <PACKAGE_DIR>
#
# Windows counterpart of copy_to_usb.sh. Copies a KeKar package to a flash
# drive, then verifies file count and hashes before reporting success.
#
# A plain copy of a PyInstaller one-folder build onto a FAT filesystem is
# thousands of small writes; an interrupted copy leaves a silently broken app.
# Always use this script, never a bare copy-and-paste.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\copy_to_usb.ps1 E: out\KeKar_Windows

param(
    [Parameter(Mandatory = $true)][string]$Destination,
    [Parameter(Mandatory = $true)][string]$Source
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
    Write-Error "Not a directory: $Destination"
}
if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    Write-Error "No such package: $Source"
}

$srcFull = (Resolve-Path -LiteralPath $Source).Path
$dstFull = (Resolve-Path -LiteralPath $Destination).Path

Write-Host "Copying $srcFull -> $dstFull (several minutes on a slow drive)..."
Copy-Item -Path (Join-Path $srcFull '*') -Destination $dstFull -Recurse -Force

Write-Host "Verifying..."
$srcFiles = Get-ChildItem -LiteralPath $srcFull -Recurse -File |
    Sort-Object -Property FullName
$dstFiles = Get-ChildItem -LiteralPath $dstFull -Recurse -File |
    Where-Object { $_.FullName -notlike "$srcFull*" } |
    Sort-Object -Property FullName

if ($srcFiles.Count -ne $dstFiles.Count) {
    Write-Error ("MISMATCH: expected {0} files, found {1}. Copy again." -f `
        $srcFiles.Count, $dstFiles.Count)
}

$srcHashes = $srcFiles | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash,
        $_.FullName.Substring($srcFull.Length)
}
$dstHashes = $dstFiles | ForEach-Object {
    "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash,
        $_.FullName.Substring($dstFull.Length)
}

$diff = Compare-Object -ReferenceObject $srcHashes -DifferenceObject $dstHashes
if ($diff) {
    Write-Error "CHECKSUM MISMATCH. Copy again."
}

Write-Host "Verified: $($srcFiles.Count) files match. Safe to eject."
