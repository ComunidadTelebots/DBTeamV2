# PowerShell script to translate lang/english_lang.lua using LibreTranslate
param(
    [string]$Source = "lang/english_lang.lua",
    [string]$OutDir = "lang",
    [int]$Delay = 1
)

$targets = @('es','fr','de','it','pt','ru','zh','ja','ko','ar','fa','tr','nl','pl','sv','no','da','fi','he','hi','ca','ca','cs','el','hu','id','ro','sk','sl','th','vi','bg','hr','lt','lv','sr','ur')
# Add more codes if desired

if (-not (Test-Path $Source)) { Write-Error "Source file $Source not found"; exit 1 }
$content = Get-Content -Raw -Path $Source -ErrorAction Stop

# extract string entries: set_text(LANG, 'key', 'value') or set_text(LANG, "key", "value")
$pattern_str_single = "set_text\s*\(\s*LANG\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*\)"
$pattern_str_double = 'set_text\s*\(\s*LANG\s*,\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)'
$pattern_num_single = "set_text\s*\(\s*LANG\s*,\s*'([^']+)'\s*,\s*([0-9]+)\s*\)"
$pattern_num_double = 'set_text\s*\(\s*LANG\s*,\s*"([^"]+)"\s*,\s*([0-9]+)\s*\)'

$texts = @{}

foreach ($m in [regex]::Matches($content, $pattern_str_single)) {
    $k = $m.Groups[1].Value
    $v = $m.Groups[2].Value
    $texts[$k] = $v
}
foreach ($m in [regex]::Matches($content, $pattern_str_double)) {
    $k = $m.Groups[1].Value
    $v = $m.Groups[2].Value
    $texts[$k] = $v
}
foreach ($m in [regex]::Matches($content, $pattern_num_single)) {
    $k = $m.Groups[1].Value
    $v = [int]$m.Groups[2].Value
    $texts[$k] = $v
}
foreach ($m in [regex]::Matches($content, $pattern_num_double)) {
    $k = $m.Groups[1].Value
    $v = [int]$m.Groups[2].Value
    $texts[$k] = $v
}

if ($texts.Count -eq 0) { Write-Error "No set_text entries found"; exit 1 }

function Escape-LuaString($s) {
    $s = $s -replace "\\", "\\\\"
    $s = $s -replace '"', '\\"'
    $s = $s -replace "`n", "\\n"
    return $s
}

$endpoint = 'https://libretranslate.de/translate'

foreach ($code in $targets) {
    if ($code -in @('en','english')) { continue }
    $outPath = Join-Path $OutDir ("$code`_lang.lua")
    Write-Host "Translating to $code -> $outPath"
    $sb = New-Object System.Text.StringBuilder
    $sb.AppendLine("-- Generated translations for $code") | Out-Null
    $sb.AppendLine() | Out-Null
    $sb.AppendLine("local LANG = '$code'") | Out-Null
    $sb.AppendLine() | Out-Null
    $sb.AppendLine("local function run(msg, matches)") | Out-Null
    $sb.AppendLine('\tif permissions(msg.from.id, msg.to.id, "lang_install") then') | Out-Null

    foreach ($kv in $texts.GetEnumerator()) {
        $k = $kv.Key
        $v = $kv.Value
        if ($v -is [int]) {
            $line = "`t`tset_text(LANG, '$k', $v)"
            $sb.AppendLine($line) | Out-Null
        } else {
            $body = @{ q = $v; source = 'en'; target = $code; format = 'text' } | ConvertTo-Json
            try {
                $resp = Invoke-RestMethod -Uri $endpoint -Method Post -Body $body -ContentType 'application/json' -ErrorAction Stop
                $translated = $resp.translatedText
                if (-not $translated) { $translated = $v }
            } catch {
                Write-Warning ("Translation failed for key " + $k + " to " + $code + ": " + $_.ToString())
                $translated = $v
            }
            $translated = Escape-LuaString $translated
            $line = ("`t`tset_text(LANG, '{0}', \"{1}\")" -f $k, $translated)
            $sb.AppendLine($line) | Out-Null
            Start-Sleep -Seconds $Delay
        }
    }

    $sb.AppendLine("`t`tif matches[1] == 'install' then") | Out-Null
    $sb.AppendLine("`t`t`treturn '`> $code installed on your bot.'") | Out-Null
    $sb.AppendLine("`t`telseif matches[1] == 'update' then") | Out-Null
    $sb.AppendLine("`t`t`treturn '`> $code updated on your bot.'") | Out-Null
    $sb.AppendLine("`t`tend") | Out-Null
    $sb.AppendLine("\telse") | Out-Null
    $sb.AppendLine("\t\treturn '\`> This plugin *requires sudo* privileged user.'") | Out-Null
    $sb.AppendLine("\tend") | Out-Null
    $sb.AppendLine("end") | Out-Null
    $sb.AppendLine() | Out-Null
    $sb.AppendLine("return { patterns = { '[!/#](install) (" + $code + "_lang)$', '[!/#](update) (" + $code + "_lang)$' }, run = run }") | Out-Null

    $sb.ToString() | Out-File -FilePath $outPath -Encoding UTF8
    Write-Host "Wrote $outPath"
}

Write-Host "All done"