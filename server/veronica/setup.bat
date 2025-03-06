@echo off
echo Creating Python virtual environment...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\Activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt

echo Hiding .env file...
attrib +h .env

echo Hiding veronica.bat file...
attrib +h veronica.bat

echo Installing Node.js dependencies...
npm install

echo Setup complete!
pause
