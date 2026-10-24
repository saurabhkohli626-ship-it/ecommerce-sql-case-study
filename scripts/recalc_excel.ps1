# Usage: powershell -File scripts/recalc_excel.ps1 -Src <full path to xlsx> [-Pdf <pdf path>]
param([string]$Src, [string]$Pdf)
# Recalculate an xlsx in Excel (via a short temp path), save it back, optionally export the Dashboard sheet to PDF.
$tmp = Join-Path $env:TEMP "ecom_dash_recalc.xlsx"
Copy-Item -LiteralPath $Src $tmp -Force
$x = New-Object -ComObject Excel.Application
$x.Visible = $false
$x.DisplayAlerts = $false
try {
    $wb = $x.Workbooks.Open($tmp)
    $x.CalculateFull()
    $wb.Save()
    if ($Pdf) {
        $ws = $wb.Worksheets.Item("Dashboard")
        $ws.PageSetup.Orientation = 2
        $ws.PageSetup.Zoom = $false
        $ws.PageSetup.FitToPagesWide = 1
        $ws.PageSetup.FitToPagesTall = 3
        $ws.ExportAsFixedFormat(0, $Pdf)
    }
    $wb.Close($false)
    "recalc ok"
} finally {
    $x.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($x)
}
Copy-Item -LiteralPath $tmp -Destination $Src -Force
Remove-Item $tmp
