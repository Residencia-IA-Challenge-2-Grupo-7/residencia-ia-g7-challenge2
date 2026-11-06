@echo off
cd /d "%~dp0\.."
echo Verificando bibliotecas do projeto...
python -m pip install -q -r requirements.txt
echo Executando Coletor TikTok 2FA (2026) no Terminal...
python src\rag\coletor_tiktok_2fa.py 15
echo Atualizando e Imprimindo o Banco de Dados Vetorial no Terminal...
python src\rag\banco_vetorial.py
pause

