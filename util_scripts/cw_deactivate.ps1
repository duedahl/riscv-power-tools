if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as an administrator."
    # Optionally, you can prompt to elevate the script:
    # if ($PSCommandPath) { Start-Process -Verb RunAs -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" }
    exit 1 # Exit with a non-zero exit code to indicate an error
}

Write-Host "PLACEHOLDER"

Start-Sleep 3
