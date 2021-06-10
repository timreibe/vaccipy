#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2017, Hiroyuki Takagi
# Code copied and adapted from pyppeteer (MIT License)
# See for pyppeteer package: https://github.com/pyppeteer/pyppeteer
# See for original code: https://github.com/pyppeteer/pyppeteer/blob/46f04c66c109353e08d873a1019df1cf4dac9dea/pyppeteer/chromium_downloader.py

"""Chromium download module."""

from io import BytesIO
from tools.clog import CLogger
import os
from pathlib import Path
import stat
import sys
import platform
from zipfile import ZipFile
import urllib3
from tqdm import tqdm
import pathlib


log = CLogger("impfterminservice")
log.set_prefix("chromium downloader")


def current_platform() -> str:
    """Get current platform name by short string."""
    if sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform.startswith('darwin'):
        if "arm" in platform.processor().lower():
            return 'mac-arm'
        else:
            return 'mac'
    elif (
        sys.platform.startswith('win')
        or sys.platform.startswith('msys')
        or sys.platform.startswith('cyg')
    ):
        if sys.maxsize > 2 ** 31 - 1:
            return 'win64'
        return 'win32'
    raise OSError('Unsupported platform: ' + sys.platform)


DEFAULT_CHROMIUM_REVISION = '869685'
chromium_revision = os.environ.get(
    'CHROMIUM_REVISION', DEFAULT_CHROMIUM_REVISION
)

vaccipy_dir = pathlib.Path(__file__).parent.absolute()
DOWNLOADS_FOLDER = Path(vaccipy_dir) / 'local-chromium'
DEFAULT_DOWNLOAD_HOST = 'https://storage.googleapis.com'
DOWNLOAD_HOST = os.environ.get(
    'PYPPETEER_DOWNLOAD_HOST', DEFAULT_DOWNLOAD_HOST
)
BASE_URL = f'{DOWNLOAD_HOST}/chromium-browser-snapshots'

REVISION = os.environ.get('PYPPETEER_CHROMIUM_REVISION', chromium_revision)

NO_PROGRESS_BAR = os.environ.get('PYPPETEER_NO_PROGRESS_BAR', '')
if NO_PROGRESS_BAR.lower() in ('1', 'true'):
    NO_PROGRESS_BAR = True  # type: ignore

# Windows archive name changed at r591479.
windowsArchive = 'chrome-win' if int(REVISION) > 591479 else 'chrome-win32'

downloadBinURLs = {
    'linux': f'{BASE_URL}/Linux_x64/{REVISION}/chrome-linux.zip',
    'mac': f'{BASE_URL}/Mac/{REVISION}/chrome-mac.zip',
    'mac-arm': f'{BASE_URL}/Mac_Arm/{REVISION}/chrome-mac.zip',
    'win32': f'{BASE_URL}/Win/{REVISION}/{windowsArchive}.zip',
    'win64': f'{BASE_URL}/Win_x64/{REVISION}/{windowsArchive}.zip',
}

downloadWebdriverURLs = {
    'linux': f'{BASE_URL}/Linux_x64/{REVISION}/chromedriver_linux64.zip',
    'mac': f'{BASE_URL}/Mac/{REVISION}/chromedriver_mac64.zip',
    'mac-arm': f'{BASE_URL}/Mac_Arm/{REVISION}/chromedriver_mac64.zip',
    'win32': f'{BASE_URL}/Win/{REVISION}/chromedriver_win32.zip',
    'win64': f'{BASE_URL}/Win_x64/{REVISION}/chromedriver_win32.zip',
}

chromiumExecutable = {
    'linux': DOWNLOADS_FOLDER / REVISION / 'chrome-linux' / 'chrome',
    'mac': (
        DOWNLOADS_FOLDER
        / REVISION
        / 'chrome-mac'
        / 'Chromium.app'
        / 'Contents'
        / 'MacOS'
        / 'Chromium'
    ),
    'mac-arm': (
        DOWNLOADS_FOLDER
        / REVISION
        / 'chrome-mac'
        / 'Chromium.app'
        / 'Contents'
        / 'MacOS'
        / 'Chromium'
    ),
    'win32': DOWNLOADS_FOLDER / REVISION / windowsArchive / 'chrome.exe',
    'win64': DOWNLOADS_FOLDER / REVISION / windowsArchive / 'chrome.exe',
}

webdriverExecutable = {
    'linux': DOWNLOADS_FOLDER
    / REVISION
    / 'chromedriver_linux64'
    / 'chromedriver',
    'mac': DOWNLOADS_FOLDER / REVISION / 'chromedriver_mac64' / 'chromedriver',
    'mac-arm': DOWNLOADS_FOLDER
    / REVISION
    / 'chromedriver_mac64'
    / 'chromedriver',
    'win32': DOWNLOADS_FOLDER
    / REVISION
    / 'chromedriver_win32'
    / 'chromedriver.exe',
    'win64': DOWNLOADS_FOLDER
    / REVISION
    / 'chromedriver_win32'
    / 'chromedriver.exe',
}


def get_url(binary: str) -> str:
    """Get download url."""
    if binary == 'chromium':
        return downloadBinURLs[current_platform()]
    elif binary == 'webdriver':
        return downloadWebdriverURLs[current_platform()]


def download_zip(url: str, binary: str) -> BytesIO:
    """Download data from url."""
    log.info(
        f'Starte den Download von {binary}. Dieser Vorgang kann einige Minuten dauern.'
    )

    # Uncomment the statement below to disable HTTPS warnings and allow
    # download without certificate verification. This is *strongly* as it
    # opens the code to man-in-the-middle (and other) vulnerabilities; see
    # https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
    # for more.
    # urllib3.disable_warnings()

    with urllib3.PoolManager() as http:
        # Get data from url.
        # set preload_content=False means using stream later.
        r = http.request('GET', url, preload_content=False)
        if r.status >= 400:
            raise OSError(
                f'{binary} downloadable not found at {url}: '
                f'Received {r.data.decode()}.\n'
            )

        # 10 * 1024
        _data = BytesIO()
        if NO_PROGRESS_BAR:
            for chunk in r.stream(10240):
                _data.write(chunk)
        else:
            try:
                total_length = int(r.headers['content-length'])
            except (KeyError, ValueError, AttributeError):
                total_length = 0
            process_bar = tqdm(total=total_length)
            for chunk in r.stream(10240):
                _data.write(chunk)
                process_bar.update(len(chunk))
            process_bar.close()

    print()
    log.info(f'Download von {binary} abgeschlossen.')
    return _data


def extract_zip(data: BytesIO, path: Path, binary: str) -> None:
    """Extract zipped data to path."""
    # On mac zipfile module cannot extract correctly, so use unzip instead.
    if current_platform() == 'mac':
        import subprocess
        import shutil

        zip_path = path / 'temp.zip'
        if not path.exists():
            path.mkdir(parents=True)
        with zip_path.open('wb') as f:
            f.write(data.getvalue())
        if not shutil.which('unzip'):
            raise OSError(
                f'Failed to automatically extract {binary}.'
                f'Please unzip {zip_path} manually.'
            )
        proc = subprocess.run(
            ['unzip', str(zip_path)],
            cwd=str(path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if proc.returncode != 0:
            log.error(proc.stdout.decode())
            raise OSError(f'Failed to unzip {zip_path}.')
        if chromium_executable().exists() and zip_path.exists():
            zip_path.unlink()
    else:
        with ZipFile(data) as zf:
            zf.extractall(str(path))
    if binary == 'chromium':
        exec_path = chromium_executable()
    elif binary == 'webdriver':
        exec_path = webdriver_executable()
    if not exec_path.exists():
        raise IOError(f'Failed to extract {binary}.')
    exec_path.chmod(
        exec_path.stat().st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR
    )
    log.info(f"{binary} exportiert nach '{path}'")


def download_chromium(binary='chromium') -> None:
    """Download and extract chromium."""
    extract_zip(
        download_zip(get_url(binary), binary),
        DOWNLOADS_FOLDER / REVISION,
        binary,
    )


def download_webdriver(binary='webdriver') -> None:
    """Download and extract webdriver."""
    extract_zip(
        download_zip(get_url(binary), binary),
        DOWNLOADS_FOLDER / REVISION,
        binary,
    )


def chromium_executable() -> Path:
    """Get path of the chromium executable."""
    return chromiumExecutable[current_platform()]


def webdriver_executable() -> Path:
    """Get path of the webdriver executable."""
    return webdriverExecutable[current_platform()]


def check_chromium() -> bool:
    """Check if chromium is placed at correct path."""
    return chromium_executable().exists()


def check_webdriver() -> bool:
    """Check if webdriver is placed at correct path."""
    return webdriver_executable().exists()


if __name__ == '__main__':
    if not check_chromium():
        download_chromium()
    if not check_webdriver():
        download_webdriver()
