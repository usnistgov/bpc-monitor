set PYTHONHASHSEED=1
pyinstaller --clean --log-level=INFO --upx-dir=".\\upx-4.2.3-win64" bpc-monitor.spec
pause