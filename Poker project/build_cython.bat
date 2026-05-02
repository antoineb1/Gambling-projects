@echo off
echo Compilation des fichiers Cython...

py -3.11 setup.py build_ext --inplace

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Compilation terminee avec succes.
) else (
    echo.
    echo Erreur pendant la compilation.
)

pause