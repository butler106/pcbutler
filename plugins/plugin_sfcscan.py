from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 시스템 파일 검사 (SFCScan) - 최종 안정화 버전
# - run() 메서드 표준화 및 cp949 인코딩 처리 적용
# - 관리자 권한 및 결과 분석 로직 통합 완료
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class SFCScanPlugin(PCButlerPlugin):
    """
    시스템 파일 검사기(sfc /scannow)를 사용하여 Windows 시스템 파일의 무결성을 검사합니다.
    """
    # 🚨 [표준] 필수 속성
    plugin_name = "SFCScan"
    description = "SFC(System File Checker)를 사용하여 시스템 파일의 오류를 검사합니다. (관리자 권한 필수)"
    
    # 🚨 [표준] __init__ 구조 통일
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    # 🚨 [표준] run 메서드에 로직 통합
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) # 로거 및 진행률 함수 연결
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        # Windows 환경 체크
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # sfc /scannow 명령 실행
            self.logger("🔄 SFC /scannow 명령 실행 중... (약 5~15분 소요될 수 있습니다)", "white")
            
            # SFC는 시간이 오래 걸리므로 timeout을 넉넉하게 900초(15분)로 설정
            # 한글 Windows 환경을 위한 인코딩('cp949')과 오류 무시('errors='ignore') 설정은 필수
            result = subprocess.run(
                ['sfc', '/scannow'],
                capture_output=True,
                text=True,
                check=False,
                timeout=900,
                encoding='cp949', 
                errors='ignore' 
            )

            self.progress(50)
            
            output = result.stdout + result.stderr

            # --------------------------------------------------------
            # SFC 결과 분석 (영문/한글 키워드 모두 대응)
            # --------------------------------------------------------
            status = "error" 
            summary = "SFC 검사 결과를 분석할 수 없습니다."
            
            if "Windows Resource Protection did not find any integrity violations" in output or "Windows 리소스 보호가 무결성 위반을 발견하지 못했습니다." in output:
                summary = "✅ SFC 검사 결과, 시스템 파일에 문제가 없습니다."
                status = "success"
                self.logger(f"  -> ✅ 시스템 파일 상태 양호.", "lime")
            elif "Windows Resource Protection found corrupt files and successfully repaired them" in output or "Windows 리소스 보호가 손상된 파일을 발견하고 성공적으로 복구했습니다." in output:
                summary = "⚠️ SFC 검사 결과, 손상된 파일이 발견되어 복구되었습니다."
                status = "warning"
                self.logger(f"  -> ⚠️ 손상 파일 발견 및 복구 완료.", "yellow")
            elif "Windows Resource Protection found corrupt files but was unable to fix some of them" in output or "Windows 리소스 보호가 손상된 파일을 발견했지만 일부를 복구할 수 없습니다." in output:
                summary = "❌ SFC 검사 결과, 손상된 파일이 발견되었으나 일부 복구에 실패했습니다."
                status = "error"
                self.logger(f"  -> ❌ 복구 실패. DISM 검사가 필요합니다.", "red")
            elif "오류: 740" in output or "관리자 권한" in output:
                summary = "❌ SFC 검사 실패: 관리자 권한이 필요합니다. (오류: 740)"
                status = "error"
                self.logger(f"  -> ❌ 관리자 권한 부족 오류.", "red")
            else:
                summary = "❌ SFC 검사 중 문제 발생 또는 결과 분석 실패. (로그 확인 필요)"
                status = "error"
                self.logger(f"  -> ❌ SFC 검사 중 오류가 감지되었습니다.", "red")
            
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환 (원본 출력 로그 포함)
            return {"status": status, "summary": summary, "output": output}
            
        except subprocess.TimeoutExpired:
            summary = "❌ SFC 검사 시간 초과 (Timeout - 15분)."
            self.logger(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}
        except Exception as e:
            error_message = f"❌ SFC 검사 중 예상치 못한 치명적인 오류 발생: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}