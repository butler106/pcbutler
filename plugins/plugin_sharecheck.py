from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 공유 폴더 점검 (ShareCheck) - 최종 안정화 수정 반영
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class ShareCheckPlugin(PCButlerPlugin):
    """
    현재 시스템에 활성화된 공유 폴더 목록을 점검합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "ShareCheck"
    description = "현재 활성화된 네트워크 공유 폴더 목록을 점검합니다."
    
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
            # net share 명령어를 사용하여 공유 폴더 목록 확인
            # 💡 [개선] shell=True 사용 시 명령어를 문자열로 전달하는 것이 표준입니다.
            command = "net share"
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='cp949', # 💡 Windows 한글 출력을 위한 cp949 인코딩 적용
                errors='ignore',
                shell=True,
                check=False,
                timeout=10 # 명령 실행 시간 초과 방지
            )
            
            output = result.stdout.strip()
            
            # 공유 목록 파싱 (관리 공유 포함)
            # 출력 첫 번째 열만 가져와서 공유 이름 파악
            shares = [line.strip().split()[0] for line in output.split('\n') if line.strip() and not line.startswith('---')]
            
            # 기본 관리 공유($로 끝나는 공유)는 제외하고 일반 사용자 공유만 확인
            user_shares = [s for s in shares if not s.endswith('$')]
            
            self.progress(70)

            if not user_shares:
                summary = "✅ 사용자 정의 공유 폴더가 발견되지 않았습니다. (양호)"
                status = "success"
                self.logger("  -> ✅ 사용자 공유 없음.", "lime")
            else:
                summary = f"⚠️ {len(user_shares)}개의 사용자 정의 공유 폴더가 활성화되어 있습니다. (보안 점검 필요: {', '.join(user_shares)})"
                status = "warning"
                self.logger(f"  -> ⚠️ 공유 폴더 발견: {', '.join(user_shares)}", "yellow")
            
            self.progress(100)
            
            return {"status": status, "summary": summary, "details": output}

        except Exception as e:
            error_message = f"❌ 공유 폴더 점검 중 치명적인 오류 발생: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}