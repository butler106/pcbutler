from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 디스크 건강 상태 점검 (DiskHealthCheck) - 최종 안정화 버전
# - 🚨 CRITICAL FIX: WMIC 연결/권한 오류 시 FATAL_ERROR 대신 WARNING 반환하도록 수정
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class DiskHealthCheckPlugin(PCButlerPlugin):
    """
    디스크의 S.M.A.R.T. 상태 등 건강 상태를 점검합니다. (wmic 사용)
    """
    # 필수 속성
    plugin_name = "DiskHealthCheck"
    description = "디스크의 S.M.A.R.T. 상태(건강 상태)를 확인합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다. (wmic 사용)", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서 최적으로 동작합니다."
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # 1. WMIC 명령어 실행
            # /failfast: WMI 연결이 실패할 경우 즉시 종료 (timeout 설정과 함께 사용 시 안전성 증가)
            command = "wmic /failfast /namespace:\\\\root\\wmi PATH MSStorageDriver_FailurePredictStatus Get PredictFailure, Reason, Active /format:list"
            self.logger(f"  -> 실행 명령어: {command}", "gray")
            
            # WMI 명령어 실행 (타임아웃 30초 설정)
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                encoding='utf-8',
                errors='ignore'
            )
            
            output = result.stdout.strip()
            # stderr에 에러 메시지가 있을 경우도 확인
            error_output = result.stderr.strip()
            
            if result.returncode != 0:
                # WMIC 명령이 시스템 환경/권한 문제로 실패한 경우 (주요 오류 해결)
                if "No active WMI connections" in error_output or "Access is denied" in error_output or not output:
                    summary = "⚠️ S.M.A.R.T. 상태 확인 실패: WMI 연결/권한 문제로 디스크 건강 상태를 확인할 수 없습니다. (경고)"
                    self.logger(summary, "yellow")
                    self.progress(100)
                    # FATAL_ERROR 대신 WARNING을 반환하여 전체 프로세스 중단 방지
                    return {"status": "warning", "summary": summary}
            
            # 2. 결과 분석 시작
            self.logger(f"  -> 명령어 실행 결과 분석 시작...", "gray")
            
            # WMI 출력이 비어있는 경우
            if not output:
                summary = "⚠️ S.M.A.R.T. 상태 확인 불가: WMI 출력이 비어있습니다."
                status = "warning"
                
            # 3. 정상 출력 분석
            elif "PredictFailure" in output:
                
                # 'PredictFailure=FALSE'는 예측 실패 없음(양호)
                if "PredictFailure=FALSE" in output:
                    summary = "✅ S.M.A.R.T. 상태: 모든 디스크 예측 실패 없음. (양호)"
                    status = "success"
                    self.logger("  -> ✅ 디스크 건강 상태 양호.", "lime")
                # 'PredictFailure=TRUE'는 고장 임박
                elif "PredictFailure=TRUE" in output:
                    summary = "❌ S.M.A.R.T. 상태: 'PredictFailure=TRUE' 감지. 디스크 교체가 시급합니다!"
                    status = "error"
                    self.logger("  -> ❌ 디스크 고장 임박 신호 감지!", "red")
                else:
                    summary = "⚠️ S.M.A.R.T. 상태를 확인할 수 없거나 예상치 못한 결과입니다. (로그 확인 필요)"
                    status = "warning"
                    self.logger("  -> ⚠️ 디스크 건강 상태 확인 불가.", "yellow")
            else:
                summary = "⚠️ S.M.A.R.T. 상태를 확인할 수 없거나 예상치 못한 결과입니다. (로그 확인 필요)"
                status = "warning"
                self.logger("  -> ⚠️ 디스크 건강 상태 확인 불가. (WMIC 출력 형식 불일치)", "yellow")

            self.progress(100)
            self.logger(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime" if status == "success" else "yellow")

            return {"status": status, "summary": summary, "details": {"wmic_output": output, "error_output": error_output}}

        except subprocess.TimeoutExpired:
            summary = "❌ [Timeout] WMIC 명령 실행 시간이 초과되었습니다. (30초)"
            self.logger(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}
            
        except Exception as e:
            # 기타 예상치 못한 오류에 대한 방어
            summary = f"❌ [치명적 오류] 디스크 건강 점검 플러그인 실행 실패: {e}"
            self.logger(summary, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": summary}