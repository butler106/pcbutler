from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_restorepoint.py
# 플러그인: 복원 지점 자동 생성 (v1.3 - 최종 안정화 및 오류 처리 완벽 반영)
import subprocess
import os

class RestorePointPlugin(PCButlerPlugin):
    """
    Windows 시스템 복원 지점을 자동으로 생성합니다.
    """
    plugin_name = "복원 지점 생성"
    description = "작업 전 시스템 복원 지점을 자동으로 생성합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
    # 🚨 [최종 안정화] run 메서드를 표준화하고, 로깅/진행률/중지 이벤트를 받도록 수정
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # --------------------------------------------------------
        # 1. Windows 환경 체크
        # --------------------------------------------------------
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        log("⚠️ 이 작업은 **관리자 권한**이 필요합니다. 권한이 없으면 실패할 수 있습니다.", "yellow")
        self.progress(30)
        
        # --------------------------------------------------------
        # 2. 복원 지점 생성 명령 실행
        # --------------------------------------------------------
        final_status = "error"
        summary = "복원 지점 생성 중 알 수 없는 오류 발생."
        
        try:
            log("🔄 복원 지점 생성 명령 실행 중...", "white")
            # PowerShell 명령: 복원 지점 생성 (Confirm:$false로 사용자 확인 생략)
            ps_command = 'Checkpoint-Computer -Description "PCButler Restore" -Confirm:$false'
            
            result = subprocess.run(
                ['powershell', '-Command', ps_command], 
                capture_output=True, 
                text=True, 
                check=False,
                timeout=60 # 복원 지점 생성은 시간이 걸릴 수 있으므로 넉넉하게 60초 설정
            )
            
            # --------------------------------------------------------
            # 3. 결과 분석 및 오류 처리
            # --------------------------------------------------------
            # returncode가 0이거나, 이미 복원 지점 생성 작업이 있음 (성공에 가까움)
            if result.returncode == 0 or "already in progress" in (result.stderr or "").lower():
                summary = "✅ 복원 지점 'PCButler Restore'가 성공적으로 생성되었거나 이미 진행 중입니다."
                log(summary, "lime")
                final_status = "success"
            else:
                # returncode가 0이 아니면 실패로 간주하고 오류 메시지 확인
                error_output = (result.stderr or result.stdout or "").strip()
                
                # 🚨 [핵심] 관리자 권한 오류 처리
                if "액세스가 거부되었습니다" in error_output or "Access is denied" in error_output or "no-root" in error_output:
                    summary = "❌ 복원 지점 생성 실패: **관리자 권한이 필요합니다.** `main.py`를 관리자 권한으로 실행해야 합니다."
                    log(summary, "red")
                else:
                    # 기타 오류
                    summary = f"❌ 복원 지점 생성 실패: PowerShell 오류 발생 (자세한 오류: {error_output[:100]}...)"
                    log(summary, "red")
                final_status = "error"

            self.progress(100)
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": summary}
            
        except subprocess.TimeoutExpired:
            summary = "❌ 복원 지점 생성 시간 초과 (60초 초과)."
            log(summary, "red")
            final_status = "error"
            self.progress(100)
            return {"status": final_status, "summary": summary}
        
        except Exception as e:
            error_message = f"❌ 복원 지점 생성 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}