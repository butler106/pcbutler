from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 자동 실행 항목 점검 (Autoruncheck) - 최종 안정화
# - 1. UnicodeDecodeError를 cp949 인코딩과 errors='ignore'로 최종 해결
# - 2. WMI 작업 후 Win32 IUnknown 해제 경고를 suppress_com_error로 제거
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import csv
from io import StringIO
import re

# 🚨 IUnknown 경고 메시지 폭주 방지 로직
try:
    import ctypes
    def suppress_com_error():
        """COM 라이브러리를 정리하여 Win32 IUnknown 해제 경고를 막습니다."""
        try:
            # CoUninitialize()는 COM 라이브러리 정리 함수입니다.
            ctypes.oledll.ole32.CoUninitialize()
        except Exception:
            pass # 정리할 COM 객체가 없으면 오류가 발생할 수 있습니다.
except ImportError:
    def suppress_com_error():
        pass

class AutoruncheckPlugin(PCButlerPlugin):
    """
    Windows 시작 시 자동 실행되는 프로그램 목록을 점검합니다.
    """
    plugin_name = "Autoruncheck" # 플러그인 이름 (test.py에 맞게 수정)
    description = "시스템 시작 시 자동 실행되는 항목을 검사하여 비정상 여부를 판단합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            command = ["wmic", "startup", "list", "full"]
            
            # 🚨 [핵심 수정]: UnicodeDecodeError 방지 (cp949 및 ignore)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='cp949', # Windows 콘솔 기본 인코딩 사용
                errors='ignore',  # 디코드 오류가 발생하면 해당 바이트 무시
                shell=True,
                check=False,
                timeout=30
            )
            
            self.progress(50)
            output = result.stdout
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            autorun_entries = [line for line in lines if line.startswith("Location=")]
            count = len(autorun_entries)
            
            self.logger(f"  -> ⚙️ [설정] 경고 기준 자동 실행 항목 수: 10개", "white")
            self.logger(f"  -> ✅ 현재 자동 실행 항목 수: {count}개", "lime" if count <= 10 else "yellow")
            
            # 샘플 항목 로그 출력
            self.logger("\n  --- (샘플 항목 최대 5개) ---", "white")
            for i in range(min(5, count)):
                path_match = re.search(r'Location=([^\r\n]+)', autorun_entries[i])
                path = path_match.group(1) if path_match else "경로 정보 없음"
                name_match = re.search(r'Caption=([^\r\n]+)', autorun_entries[i])
                name = name_match.group(1) if name_match else f"항목 #{i+1}"
                self.logger(f"  {i+1}. {name}: {path}", "gray")
            if count > 5:
                self.logger(f"  ... 외 {count - 5}개 항목이 더 있습니다. (총 {count}개)", "gray")

            if count > 10:
                final_summary = f"자동 실행 항목이 {count}개로 다소 많습니다."
                final_status = "warning"
            else:
                final_summary = f"자동 실행 항목 {count}개 확인 완료. 상태 양호."
                final_status = "success"

            self.logger(f"\n✅ '{self.name}' 작업을 완료했습니다.", "lime")
            self.progress(100)
            
            # 🚨 [IUnknown Fix 적용]
            suppress_com_error()
            
            return {"status": final_status, "summary": final_summary}

        except Exception as e:
            error_message = f"❌ [오류] 자동 실행 항목 점검 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            
            # 🚨 [IUnknown Fix 적용]
            suppress_com_error()
            
            return {"status": "error", "summary": error_message}