from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: Windows 이미지 복구 검사 (Dismcheck) - 권한 및 안정화 버전
# - 🚨 관리자 권한 선제 체크 로직 적용 (성능 개선)
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import ctypes # 🚨 [추가] 관리자 권한 체크를 위한 라이브러리 추가

class DISMCheckPlugin(PCButlerPlugin):
    """
    DISM(Deployment Image Servicing and Management) 도구를 사용하여 
    Windows 시스템 이미지의 무결성을 검사합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "Dismcheck"
    description = "DISM을 사용하여 Windows 시스템 이미지의 오류를 검사합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다. (DISM ScanHealth)", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        # 🚨 [핵심 수정] 1. 관리자 권한 선제 검사
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            is_admin = False
            
        if not is_admin:
            summary = "❌ DISM 검사 실패: **관리자 권한으로 실행해야 합니다.**"
            status = "error"
            self.logger(summary, "red")
            self.progress(100)
            # 관리자 권한이 없으면 즉시 종료 (5분 대기 방지)
            return {"status": status, "summary": summary, "details": "Error: Elevated privileges required to run DISM command."}

        self.progress(10)
        
        try:
            # 1단계: 이미지 검사 (ScanHealth)
            self.logger("  -> 🔍 1/2단계: Windows 이미지 검사 시작 (ScanHealth)... (최대 5분 소요)", "yellow")
            command_scan = ["Dism", "/Online", "/Cleanup-Image", "/ScanHealth"]
            
            # I/O Deadlock 방지 로직 (유지)
            result_scan = subprocess.run(
                command_scan,
                capture_output=True,
                shell=True,
                check=False,
                timeout=300 # 5분 대기
            )
            
            # 수동 디코딩 (유지)
            output = ""
            try:
                output = result_scan.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                output = result_scan.stdout.decode('utf-8', errors='ignore').strip()

            self.logger(f"  -> ℹ️ DISM 검사 결과 로그 (일부): {output[:100]}...", "gray")
            
            self.progress(50)
            
            # 🚨 [수정] 선제 체크를 했으므로 returncode 740에 대한 명시적 체크를 제거하여 로직 간소화
            
            # 🚨 [명령 실행 실패 체크]: 일반적인 오류 코드
            if result_scan.returncode != 0:
                summary = f"❌ DISM 명령 실행 실패 (코드: {result_scan.returncode}). 시스템 이미지 확인 불가."
                status = "error"
                self.logger(summary, "red")
                self.progress(100)
                return {"status": status, "summary": summary, "details": output if output else f"DISM 명령 실행 실패 (Exit Code: {result_scan.returncode})"}
            
            # 2단계: 이미지 상태 확인 및 결과 분석 (간단화)
            if "No component store corruption detected" in output or "작업을 완료했습니다." in output:
                summary = "✅ DISM 검사 결과, 시스템 이미지 손상이 발견되지 않았습니다. (양호)"
                status = "success"
                self.logger(f"  -> ✅ 이미지 상태 양호.", "lime")
            elif "The operation completed successfully" in output:
                summary = "⚠️ DISM 작업이 성공적으로 완료되었으나 상세 내용 확인 필요. (주의)"
                status = "warning"
                self.logger(f"  -> ⚠️ DISM 작업 완료. 로그 확인 필요.", "yellow")
            else:
                summary = "❌ DISM 검사 중 문제 발생 또는 결과 분석 실패. (로그 확인 필요)"
                status = "error"
                self.logger(f"  -> ❌ DISM 검사 중 오류가 감지되었습니다.", "red")
            
            self.progress(100)
            
            return {"status": status, "summary": summary, "details": output}

        except Exception as e:
            error_message = f"❌ [오류] DISM 검사 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}