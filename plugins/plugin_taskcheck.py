from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 작업 스케줄러 점검 (TaskCheck) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class TaskCheckPlugin(PCButlerPlugin):
    """
    Windows 작업 스케줄러에 등록된 작업 목록을 확인합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "TaskCheck"
    description = "Windows 작업 스케줄러에 등록된 작업 목록을 확인합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # schtasks /query /fo list 명령어를 사용하여 작업 목록 확인
            # 간단한 작업 개수만 파악
            command = ["schtasks", "/query"]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='cp949', 
                errors='ignore',
                shell=True,
                check=False,
                timeout=30
            )
            
            output = result.stdout.strip()
            
            # 작업 이름(TaskName)의 개수 세기
            task_count = output.lower().count("taskname:") + output.lower().count("작업 이름:")
            
            self.progress(70)

            if task_count == 0:
                summary = "⚠️ 작업 스케줄러에서 작업을 찾을 수 없습니다. (비정상일 수 있음)"
                status = "warning"
                self.logger("  -> ⚠️ 작업 스케줄러에 등록된 작업이 없습니다.", "yellow")
            else:
                # 윈도우 기본 작업이 많으므로 100개 이하를 양호로 가정
                if task_count > 100:
                    summary = f"⚠️ 작업 스케줄러에 {task_count}개의 작업이 등록되어 있습니다. (점검 필요)"
                    status = "warning"
                    self.logger(f"  -> ⚠️ 등록된 작업이 {task_count}개로 다소 많습니다.", "yellow")
                else:
                    summary = f"✅ 작업 스케줄러에 {task_count}개의 작업이 등록되어 있습니다. (양호)"
                    status = "success"
                    self.logger(f"  -> ✅ 등록된 작업: {task_count}개.", "lime")
            
            self.progress(100)
            
            return {"status": status, "summary": summary, "task_count": task_count}

        except Exception as e:
            error_message = f"❌ [오류] 작업 스케줄러 점검 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}