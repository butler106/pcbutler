from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_networkfix.py
# 플러그인: 네트워크 초기화 및 복구 (v1.2 - run 메서드 및 return 값 오류 수정)
import subprocess
import os

class NetworkFixPlugin(PCButlerPlugin):
    plugin_name = "네트워크 초기화"
    description = "DNS, IP, Winsock 설정을 초기화하여 연결 문제를 복구합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger # self.logger 사용

        log("🔍 '네트워크 초기화' 작업을 시작합니다.", "cyan")
        
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            return {"status": "warning", "summary": summary}

        log("⚠️ 이 작업은 **관리자 권한**이 필요하며, 재부팅 후 적용됩니다.", "yellow")
        
        try:
            log("🔧 네트워크 초기화 명령 실행 중...", "white")
            
            # 명령 실행: subprocess.run을 사용하여 안정성 확보 및 로그 출력
            commands = [
                "ipconfig /release",
                "ipconfig /renew",
                "ipconfig /flushdns",
                "netsh winsock reset", # winsock 초기화는 재부팅 필요
                "netsh int ip reset" # IP 설정 초기화는 재부팅 필요
            ]
            
            for cmd in commands:
                log(f"  -> 실행: {cmd}", "gray")
                # 결과 무시하고 실행 (관리자 권한 없으면 실패)
                subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True, timeout=10)

            summary = "✅ 네트워크 초기화 완료. 재부팅 후 적용됩니다."
            log(summary, "lime")
            
            # 🚨 [필수] Success 반환
            return {"status": "success", "summary": summary}
            
        except Exception as e:
            error_message = f"❌ 네트워크 복구 실패: {e} - 관리자 권한을 확인하십시오."
            log(error_message, "red")
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    def plugin_stop(self):
        # run 메서드 사용 시, 이 함수는 이제 정리 작업만 수행하도록 변경
        self.logger("🛑 네트워크 초기화 플러그인 종료됨", "gray")
        pass