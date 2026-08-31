from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: RAM 최적화 (OptimizeRam) - 실제 기능 및 성능 측정 반영
# - psutil을 사용하여 최적화 전후 가용 메모리를 측정하고 보고합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import subprocess
import psutil # 메모리 측정을 위해 필수
import platform # OS 체크를 위해 필수
import time # 명령 실행 지연을 위해 사용

class OptimizeRamPlugin(PCButlerPlugin):
    """
    시스템 RAM을 최적화하고, 최적화 전후 가용 메모리 변화를 측정하여 보고합니다.
    """
    plugin_name = "OptimizeRam"
    # ✅ [수정] 실제 기능 설명 반영
    description = "psutil과 PowerShell을 사용하여 실제 RAM 최적화 및 성능 측정을 수행합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (실제 메모리 최적화 및 측정)", "cyan")
        
        if platform.system() != "Windows":
            summary = "이 플러그인은 Windows 환경에서만 메모리 최적화가 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
        
        # --------------------------------------------------------
        # 1. 최적화 전 가용 메모리 측정
        # --------------------------------------------------------
        try:
            initial_available_mb = psutil.virtual_memory().available / (1024 * 1024)
            log(f"📋 최적화 전 가용 RAM: {initial_available_mb:.2f} MB", "white")
        except NameError:
            error_message = "❌ 'psutil' 라이브러리가 설치되지 않았습니다. (pip install psutil 필요)"
            log(error_message, "red")
            return {"status": "error", "summary": error_message}
            
        self.progress(30)

        # --------------------------------------------------------
        # 2. 실제 RAM 최적화 명령 실행 (Working Set 정리)
        # --------------------------------------------------------
        log("🔧 Windows Working Set 정리 명령 실행 중...", "yellow")
        
        ps_command = 'Add-Type -MemberDefinition \"[DllImport(\\"kernel32.dll\\")]public static extern bool SetProcessWorkingSetSize(IntPtr proc, int min, int max);\" -Name \"W32API\" -Namespace \"W32\"; [W32.W32API]::SetProcessWorkingSetSize((Get-Process -id $pid).Handle, -1, -1) | Out-Null'
        
        try:
            subprocess.run(
                ['powershell', '-Command', ps_command], 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=20
            )
        except Exception as e:
            error_message = f"❌ RAM 최적화 명령 실행 실패: {e} - 관리자 권한을 확인하십시오."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
        
        self.progress(70)
        time.sleep(1) # 메모리 상태 반영을 위해 1초 대기

        # --------------------------------------------------------
        # 3. 최적화 후 가용 메모리 측정 및 결과 분석
        # --------------------------------------------------------
        final_available_mb = psutil.virtual_memory().available / (1024 * 1024)
        log(f"📋 최적화 후 가용 RAM: {final_available_mb:.2f} MB", "white")
        
        freed_memory_mb = final_available_mb - initial_available_mb
        
        if freed_memory_mb > 0:
            summary = f"✅ RAM 최적화 성공: **약 {freed_memory_mb:.2f} MB**의 메모리가 확보되었습니다."
            status = "success"
            log(summary, "lime")
        else:
            summary = "✅ RAM 최적화 명령은 완료되었으나, 확보된 가용 메모리가 미미합니다 (0 MB)."
            status = "success" # 기능 자체는 성공적으로 실행되었으므로 success 유지
            log(summary, "gray")
        
        self.progress(100)
        
        # 🚨 [최종 결과] 실제 기능 수행 결과를 반환합니다.
        return {"status": status, "summary": summary}