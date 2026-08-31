# -*- mode: python ; coding: utf-8 -*-
# PC Butler GUI 빌드 스펙 (2026-08-31 신규 작성)
#
# 기존 butler_launcher.spec은 butler_launcher.py를 진입점으로 삼았는데,
# butler_launcher.py는 지금의 main_window.MainWindow 생성자 시그니처
# (MainWindow(executor, plugin_classes, plugins_by_group, config)) 대신
# 인자 없는 옛날 방식(MainWindow())으로 호출하고 있어서 그대로 빌드하면
# 즉시 TypeError로 죽는다. 반면 main.py는 이미 GUI 모드에서 이 모든 초기화
# (플러그인 메타데이터 로드, 플러그인 클래스 로드, config.ini 로드)를 올바르게
# 수행한 뒤 MainWindow를 생성하므로, main.py를 그대로 진입점으로 쓴다.
#
# plugins/*.py는 main.py가 importlib으로 "동적으로" 로드하기 때문에
# PyInstaller의 정적 분석만으로는 자동 포함되지 않는다 — 반드시 datas에
# 실제 폴더째로 넣어서, 빌드된 exe 옆에 진짜 .py 파일로 남아있게 해야 한다.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins', 'plugins'),
        ('config.ini', '.'),
        ('plugin_index_categorized.txt', '.'),
        ('config', 'config'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pcbutler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # 🚨 console=False (windowed) 모드에서는 sys.stdout/stderr가 None이 되는데,
    # 오늘 세션에서 이미 15개 플러그인의 sys.stdout.detach() 문제를 고쳐뒀으므로
    # (reconfigure() 기반, None-safe) 이 모드로 빌드해도 안전하다.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # 아이콘(butler.ico)은 이번 GitHub Actions 빌드 묶음에 포함하지 않았다.
    # 굳이 필요하면 나중에 icon=['butler.ico']를 추가하고 그 파일도 레포에 올리면 된다.
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pcbutler',
)
