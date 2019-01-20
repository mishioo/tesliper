@echo off

set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"
set TSLRDIR=%~dp0..
echo %TSLRDIR%

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = "%TSLRDIR%\Tesliper.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.IconLocation = "%TSLRDIR%\tesliper.ico" >> %SCRIPT%
echo oLink.TargetPath = "%TSLRDIR%\bin\tesliper_gui.bat" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%
copy "%TSLRDIR%\Tesliper.lnk" "%USERPROFILE%\Desktop\Tesliper.lnk"