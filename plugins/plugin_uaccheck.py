from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_uaccheck.py
# 플러그인: 사용자 계정 권한 점검 (v1.1 - NoneType 오류 및 표준 구조 적용)
import ctypes
import os

class UACCheckPlugin(PCButlerPlugin):
    plugin_name = "사용자 계정 권한 점검"
    description = "현재 계정이 관리자 권한을 가지고 있는지 확인하여 안전한 실행 환경을 점검합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(30)

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            
            if is_admin:
                summary = "✅ 현재 계정은 **관리자 권한**을 가지고 있습니다. 모든 작업이 가능합니다."
                log(summary, "lime")
                final_status = "success"
            else:
                summary = "⚠️ 현재 계정은 **관리자 권한이 없습니다**. 일부 시스템 변경 작업(네트워크 초기화, 복원 지점 생성 등)이 제한되거나 실패할 수 있습니다."
                log(summary, "yellow")
                final_status = "warning"
                
            self.progress(100)
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": summary}

        except Exception as e:
            error_message = f"❌ 사용자 계정 권한 점검 실패: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경 (불필요한 return 제거)
    def plugin_stop(self):
        self.logger("🛑 사용자 계정 권한 점검 플러그인 종료됨", "gray")
        pass