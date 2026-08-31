from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import platform
import psutil # CPU 정보 수집을 위해 추가
import sys # 인코딩 정보 수집을 위해 추가

class OSInfoPlugin(PCButlerPlugin):
    """
    운영체제(OS)의 기본 정보를 수집하고 요약합니다.
    """
    plugin_name = "OSInfo"
    description = "운영체제(OS)의 기본 정보를 수집합니다."
    version = "1.2.0" # CPU 정보 추가 반영

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name

    # 타입 힌트를 포함한 표준 run 메서드 정의
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger

        log(f"🔍 '{self.name}' 작업을 시작합니다. (OS 기본 정보 수집)", "cyan")
        self.progress(1)

        try:
            # 🚨 중단 확인 로직 통일: stop_check() 사용
            if stop_check and stop_check():
                log("  -> ⚠️ OS 정보 수집 중단 요청 수신.", "yellow")
                return {"status": "warning", "summary": "⚠️ 사용자 요청으로 OS 정보 수집 중단됨."}

            # OS 기본 정보 수집
            system_info = platform.uname()
            
            # 추가 정보 수집 (CPU/프로세서 정보)
            processor_info = platform.processor()
            cpu_count = psutil.cpu_count(logical=True)
            
            # 결과 저장
            details = {
                "system": system_info.system,
                "release": system_info.release,
                "version": system_info.version,
                "architecture": system_info.machine,
                "platform_string": platform.platform(),
                "processor": processor_info,
                "cpu_logical_count": cpu_count,
                "encoding": sys.getfilesystemencoding()
            }

            summary = f"✅ OS 정보 수집 완료: {system_info.system} {system_info.release} ({system_info.machine})"
            log(summary, "lime")

            final_result = {"status": "success", "summary": summary, "details": details}
            self.progress(100)
            
            # 🚨 [CRITICAL FIX]: JSON 결과 파일 저장 (ReportMerge를 위해 필수)
            self._save_result_to_file(final_result)
            
            return final_result

        except Exception as e:
            error_message = f"❌ OS 정보 수집 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": error_message}
