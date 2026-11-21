# Exports ISE-A5-Final-Report.docx to PDF with Microsoft Word (Windows). Run from report/:  powershell -File export_pdf.ps1
$ErrorActionPreference = 'Stop'
$docx = Join-Path $PSScriptRoot 'ISE-A5-Final-Report.docx'
$pdf  = Join-Path $PSScriptRoot 'ISE-A5-Final-Report.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0                   # wdAlertsNone: no hidden dialogs
try {
    # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles)
    $doc = $word.Documents.Open($docx, $false, $true, $false)
    $doc.ExportAsFixedFormat($pdf, 17)   # 17 = wdExportFormatPDF
    $pages = $doc.ComputeStatistics(2)    # 2 = wdStatisticPages
    $doc.Close($false)
    Write-Output "wrote $pdf ($pages pages)"
} finally {
    $word.Quit()
}
