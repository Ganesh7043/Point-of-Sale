@echo off
echo Starting Simple POS... Press CTRL+C to stop.
echo   Admin:   http://127.0.0.1:5000/admin  (admin / admin123)
echo   Billing: http://127.0.0.1:5000/billing (staff1 / staff123)
set PYTHONIOENCODING=utf-8
python run.py
pause
