param([string]$TestPath = "backend/tests", [Parameter(ValueFromRemainingArguments=$true)]$Args)
$env:PYTHONPATH = "$PWD\backend\backend"
pytest $TestPath $Args
exit $LASTEXITCODE
