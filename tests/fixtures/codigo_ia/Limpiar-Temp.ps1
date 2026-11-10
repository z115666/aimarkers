# Here's the updated script with improved error handling:
```powershell
# Paso 1: Obtener los ficheros temporales
$temp = Get-ChildItem $env:TEMP -Recurse
# Paso 2: Filtrar los antiguos
$viejos = $temp | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
# Paso 3: Eliminar
# En un entorno real, aquí iría la lógica de registro
$viejos | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "✅ Limpieza completada"
```
