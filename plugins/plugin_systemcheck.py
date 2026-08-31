from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 종합 시스템 점검 (SystemCheck) - 기능 구현 버전
# - psutil을 사용하여 CPU, 메모리, 디스크의 주요 상태를 점검하고 진행률을 업데이트합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import psutil # 시스템 상태 점검을 위해 필수 모듈 추가
import platform
import time 

class SystemCheckPlugin(PCButlerPlugin):
    """
    시스템의 전반적인 상태(CPU, 메모리, 디스크)를 종합적으로 점검합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "SystemCheck"
    # 🌟 [수정] 설명: 실제 시스템 상태 점검 기능을 명시
    description = "psutil을 사용하여 CPU, 메모리, 디스크의 전반적인 상태를 종합적으로 점검합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (CPU/메모리/디스크 상태 점검)", "cyan")

        if os.name != "nt" and platform.system() != "Linux":
            summary = "이 플러그인은 Windows 및 Linux 환경에서만 시스템 점검이 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
        
        # --------------------------------------------------------
        # 💡 [구현 로직] psutil을 사용한 실질적인 시스템 상태 점검
        # --------------------------------------------------------
        
        details = {}
        issues_found = []
        
        # 1. CPU 사용률 점검
        self.progress(10)
        log("🔄 1/3: CPU 사용률 점검 중...", "white")
        cpu_percent = psutil.cpu_percent(interval=1) 
        details["cpu_usage"] = f"{cpu_percent}%"
        if cpu_percent > 80:
            issues_found.append(f"CPU 사용률이 높음 ({cpu_percent}%)")
            
        # 2. 메모리 사용률 점검
        self.progress(40)
        log("🔄 2/3: 메모리 사용률 점검 중...", "white")
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        details["memory_usage"] = f"{mem_percent}% (총: {mem.total // (1024**3)}GB)"
        if mem_percent > 90:
            issues_found.append(f"메모리 사용률이 매우 높음 ({mem_percent}%)")

        # 3. 디스크 사용률 점검 (C: 드라이브 기준)
        self.progress(70)
        log("🔄 3/3: 디스크 사용률 점검 중 (C:)...", "white")
        try:
            disk = psutil.disk_usage('C:\\' if platform.system() == "Windows" else '/')
            disk_percent = disk.percent
            details["disk_usage"] = f"{disk_percent}% (총: {disk.total // (1024**3)}GB)"
            if disk_percent > 95:
                issues_found.append(f"디스크 공간이 부족함 ({disk_percent}%)")
        except Exception as e:
            details["disk_usage"] = "점검 실패"
            issues_found.append(f"디스크 점검 실패: {e}")

        # 4. 최종 분석 및 보고
        self.progress(90)
        
        if issues_found:
            summary = f"⚠️ 종합 점검 결과, **{len(issues_found)}개**의 시스템 이상 징후가 감지되었습니다."
            final_status = "warning"
            log(f"  -> 🚨 감지된 문제: {', '.join(issues_found)}", "yellow")
        else:
            summary = "✅ 시스템의 주요 상태(CPU/메모리/디스크)는 모두 양호합니다."
            final_status = "success"

        self.progress(100)
        
        # 🚨 [필수] 최종 결과 반환
        return {"status": final_status, "summary": summary, "details": details}