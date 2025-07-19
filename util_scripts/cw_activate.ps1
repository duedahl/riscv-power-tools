############### Check for elevation ###############
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as an administrator."
    exit 1 # Exit with a non-zero exit code to indicate an error
}
#############################################################

# Ensure that the WSL service is running
wsl --status

############### Check for connected devices ################
Write-Host "Clearing Persisted USB Connections."
usbipd detach --all
usbipd unbind --all
Start-Sleep -Seconds 1
$usbipdList = usbipd list

# FIXME: Also save bus states, to avoid binding already bound USB devices.
$busIds = $usbipdList | Select-String -Pattern "ChipWhisperer|USB Serial Converter" | ForEach-Object {
    ($_.Line -split " ")[0]
}

$huskyPresent = $false
if ($usbipdList -match "Husky") {
    $huskyPresent = $true
}

if (-not $busIds) {
    Write-Host "ChipWhisperer or USB Serial Converter not found."
    Write-Host "Please connect the ChipWhisperer device."
    Start-Sleep -Seconds 5 # Wait for 5 seconds
    Write-Host "Exiting script."
    exit
}
#############################################################
# Bind + Attach loop with retries to account for weirdly unstable Husky
function BindAndAttachDevices {
    param (
        [string[]]$busIds, # Array of bus IDs
        [int]$maxAttempts = 3 # Maximum number of attempts
    )
    
    $attempt = 1
    $allAttached = $false
    
    while (-not $allAttached -and $attempt -le $maxAttempts) {
        Write-Host "Attempt $attempt of $maxAttempts"
        Start-Sleep -Seconds 1
        # Process each device
        foreach ($busId in $busIds) {
            $status = usbipd list | Select-String -Pattern $busId
            
            # Check if binding is needed
            if ($status -match "Not shared") {
                Write-Host "Binding BUSID: $busId"
                usbipd bind --busid $busId
            }
            else {
                Write-Host "BUSID: $busId already bound, skipping bind"
            }

            $status = usbipd list | Select-String -Pattern $busId
            
            # Check if attachment is needed
            if ($status -match "Shared") {
                Write-Host "Attaching BUSID: $busId"
                usbipd attach --wsl --busid $busId --host-ip $staticIP
            }
            else {
                Write-Host "BUSID: $busId already attached/shared, skipping attach"
            }
            Start-Sleep -Seconds 4
        }
        
        # Verify all devices are attached
        $allAttached = $true
        foreach ($busId in $busIds) {
            $status = usbipd list | Select-String -Pattern $busId
            if ($status -notmatch "Attached") {
                Write-Warning "Device $busId is not attached/shared"
                $allAttached = $false
            }
        }
        
        if ($allAttached) {
            Write-Host "Success: All devices are attached/shared"
        }
        else {
            if ($attempt -lt $maxAttempts) {
                Write-Host "Not all devices attached, trying again in 2 seconds..."
                Start-Sleep -Seconds 2
            }
            else {
                Write-Error "Failed to attach all devices after $maxAttempts attempts"
            }
        }
        
        $attempt++
    }
}

BindAndAttachDevices -busIds $busIds

Write-Host "ChipWhisperer and USB Serial Converter devices bound and attached."

Start-Sleep 2
