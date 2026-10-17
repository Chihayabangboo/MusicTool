@echo off
chcp 65001 >nul
setlocal

rem 定位项目根目录，不硬编码绝对路径
cd /d "%~dp0"
set "PYTHONUTF8=1"

echo ============================================
echo  Music Toolkit - 本地音乐格式识别与转换
echo ============================================

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python。
    echo 请安装 Python 3.10 或更高版本，并勾选 "Add Python to PATH"。
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 版本低于 3.10，请升级后再运行。
    pause
    exit /b 1
)

python -c "import music_toolkit" >nul 2>&1
if errorlevel 1 (
    echo [安装] 首次运行，正在安装 music-toolkit...
    python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] music-toolkit 安装失败，请检查网络或 Python 环境。
        pause
        exit /b 1
    )
) else (
    echo [检查] music-toolkit 已安装，跳过安装。
)

python -c "import ttkbootstrap, tkinterdnd2, mutagen" >nul 2>&1
if errorlevel 1 (
    echo [依赖] GUI 或元数据依赖缺失，正在尝试安装...
    python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败。
        pause
        exit /b 1
    )
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    python -c "import imageio_ffmpeg" >nul 2>&1
    if errorlevel 1 (
        echo [提示] 未检测到 ffmpeg，转码功能不可用；格式识别功能仍可使用。
    ) else (
        echo [检查] 未检测到系统 ffmpeg，但检测到可选的 imageio-ffmpeg。
    )
) else (
    echo [检查] 已检测到 ffmpeg。
)


echo [启动] 正在启动图形界面...
python -m pip install ncmdump-py pycryptodome -i https://pypi.tuna.tsinghua.edu.cn/simple
python -c "import ncmdump"
python -m music_toolkit
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，错误码: %errorlevel%
    pause
)

endlocal
