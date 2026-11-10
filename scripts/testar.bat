@echo off
REM ==============================================================================
REM Atalho de Testes para Windows CMD / PowerShell (Grupo 7)
REM ==============================================================================
echo [DOCKER] Executando testes automatizados dentro do container Docker...
docker compose run --rm app pytest -v %*
if %ERRORLEVEL% equ 0 (
    echo [SUCESSO] Todos os testes passaram!
) else (
    echo [FALHA] Alguns testes falharam. Verifique os logs acima.
)
