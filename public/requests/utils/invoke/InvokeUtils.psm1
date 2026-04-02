
function Invoke-ApiWithKeyRotation {
    param(
        [Parameter(Mandatory)]
        [string]$Url,

        [string[]]$Keys,

        [hashtable]$BaseHeaders = @{},

        [int]$MaxRetries = 4,
        [int]$InitialDelaySec = 2,

        [string]$KeyHeaderName = "X-API-Key"
    )

    function Invoke-With-Retry {
        param(
            [string]$Url,
            [hashtable]$Headers
        )

        $attempt = 0
        $delay = $InitialDelaySec

        while ($attempt -lt $MaxRetries) {
            try {
                return Invoke-RestMethod `
                    -Uri $Url `
                    -Headers $Headers `
                    -TimeoutSec 60 `
                    -ErrorAction Stop
            }
            catch {
                $attempt++

                $statusCode = $null
                if ($_.Exception.Response) {
                    $statusCode = $_.Exception.Response.StatusCode.Value__
                }

                $message = $_.Exception.Message

                # -----------------------------
                # Network errors
                # -----------------------------
                if ($message -match "Connection reset|transport connection|underlying connection was closed|Unable to read data") {
                    if ($attempt -lt $MaxRetries) {
                        Write-Warning "Network issue → retry in $delay sec..."
                        Start-Sleep -Seconds $delay
                        $delay = [Math]::Min($delay * 2, 30)
                        continue
                    }
                }

                # -----------------------------
                # Server errors (5xx)
                # -----------------------------
                if ($statusCode -ge 500 -and $attempt -lt $MaxRetries) {
                    Write-Warning "Server error $statusCode → retry in $delay sec..."
                    Start-Sleep -Seconds $delay
                    $delay = [Math]::Min($delay * 2, 30)
                    continue
                }

                throw $_
            }
        }

        throw "Max retries reached for request: $Url"
    }

    # -------------------------------------------------
    # CASE 1: No API Keys (z.B. Sleeper API)
    # -------------------------------------------------
    if (-not $Keys -or $Keys.Count -eq 0) {
        Write-Host "Invoke without API key..." -ForegroundColor DarkGray

        $result = Invoke-With-Retry -Url $Url -Headers $BaseHeaders

        return [PSCustomObject]@{
            Result = $result
            Key    = $null
        }
    }

    # -------------------------------------------------
    # CASE 2: With API Key Rotation
    # -------------------------------------------------
    foreach ($key in $Keys) {

        $headers = @{}
        $headers += $BaseHeaders
        $headers[$KeyHeaderName] = $key

        try {
            Write-Host "Try with key: $key" -ForegroundColor DarkGray

            $result = Invoke-With-Retry -Url $Url -Headers $headers

            return [PSCustomObject]@{
                Result = $result
                Key    = $key
            }
        }
        catch {
            $statusCode = $null
            if ($_.Exception.Response) {
                $statusCode = $_.Exception.Response.StatusCode.Value__
            }

            if ($statusCode -eq 429) {
                Write-Warning "429 Too Many Requests → switching key..."
                continue
            }

            Write-Warning "Key failed → trying next..."
            continue
        }
    }

    throw "All API keys exhausted for request: $Url"
}