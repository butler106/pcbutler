from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 원격 데스크톱 설정 점검 (RDPCheck) - 최종 완벽 버전
# - RDP 활성화 여부를 레지스트리에서 직접 확인하고 보안 경고를 반환합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import sys

class RDPCheckPlugin(PCButlerPlugin):
    """
    RDP (원격 데스크톱) 기능의 활성화 여부를 Windows 레지스트리에서 점검하여
    외부 접속 가능성을 진단합니다.
    """
    plugin_name = "원격 데스크톱 설정 점검"
    description = "RDP 기능의 활성화 여부와 외부 접속 가능성을 점검합니다."
    version = "2.0.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🖥️ '{self.plugin_name}' 점검을 시작합니다.", "cyan")
        self.progress(10)

        # 1. OS 환경 체크 (Windows 전용)
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}

        final_status = "error" # 기본값 설정
        final_summary = "RDP 점검 중 알 수 없는 오류 발생."

        try:
            # 2. PowerShell 명령어 구성
            # (fDenyTSConnections: 1=비활성화/거부 (보안 양호), 0=활성화/허용 (보안 주의))
            cmd = (
                'powershell.exe -Command '
                '\"(Get-ItemProperty -Path \'HKLM:\\\\System\\\\CurrentControlSet\\\\Control\\\\Terminal Server\').fDenyTSConnections\"'
            )
            
            # 3. 명령 실행 및 결과 획득
            result = ""
            try:
                # check_output으로 실행하고, 시스템 기본 인코딩으로 디코딩하여 결과만 받습니다.
                result_bytes = subprocess.check_output(cmd, shell=True, timeout=10)
                # 시스템 인코딩으로 디코딩 (UnicodeDecodeError 방지)
                result = result_bytes.decode(sys.getfilesystemencoding(), errors='ignore').strip()
                log(f"  -> RDP 레지스트리 값 (fDenyTSConnections) 획득: {result}", "gray")
                self.progress(50)
                
            except subprocess.CalledProcessError as e:
                error_output = e.stderr.decode(sys.getfilesystemencoding(), errors='ignore').strip()
                log(f"⚠️ PowerShell 명령 실행 실패: {error_output}", "yellow")
            except subprocess.TimeoutExpired:
                log("⚠️ PowerShell 명령 시간 초과. (10초)", "yellow")
            except Exception as e:
                log(f"⚠️ RDP 명령어 실행 중 예외 발생: {type(e).__name__}", "yellow")
                
            self.progress(70)

            # 4. 결과 분석
            if result == "1":
                final_summary = "✅ 원격 데스크톱 비활성화됨 → 외부 접속 차단 상태 (양호)"
                final_status = "success"
                log(final_summary, "lime")
            elif result == "0":
                final_summary = "⚠️ 원격 데스크톱 활성화됨 → 외부 접속 가능 → 보안 정책 확인 필요 (주의)"
                final_status = "warning"
                log(final_summary, "yellow")
            else:
                # result가 빈 문자열이거나 예상치 못한 값일 경우 (예: 레지스트리 키 부재)
                final_summary = "ℹ️ RDP 설정 정보 해석 불가 또는 레지스트리 키 부재 → 수동 확인 권장"
                final_status = "info"
                log(final_summary, "white")
        
        except Exception as e:
            final_summary = f"❌ RDP 점검 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            final_status = "error"
            log(final_summary, "red")

        self.progress(100)
        
        # 5. 최종 결과 반환
        return {"status": final_status, "summary": final_summary}