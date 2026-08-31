from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 사용자 피드백 수집 (Feedback) - 안정화 버전
# - 비대화형 환경(자동 실행)에서의 EOFError 및 return 값 누락 문제 해결
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
from datetime import datetime
import sys
import io
import time
import builtins # input() 호출을 위해 추가

# 콘솔 인코딩 문제 방지 (플러그인 레벨에서는 주석 처리 권장: 메인 스크립트에서 관리)
# try:
#     sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
#     sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
# except:
#     pass

class FeedbackPlugin(PCButlerPlugin):
    """
    진단 결과에 대한 사용자 의견이나 개선 요청을 기록합니다.
    """
    plugin_name = "사용자 피드백 수집"
    description = "진단 결과에 대한 사용자 의견이나 개선 요청을 기록합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.feedback_dir = os.path.join(base_path, "reports")
        self.feedback_file = os.path.join(self.feedback_dir, "feedback_log.txt")

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        # logger와 progress는 run 메서드 호출 시 이미 설정됩니다.
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger # 로깅 함수 별칭 설정
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")

        try:
            self.progress(10)
            
            # 1. 사용자 입력 요청
            # 🚨 [개선]: input() 대신 builtins.input()을 명시적으로 사용.
            log("\n💬 개선할 점이나 의견이 있으시면 입력해 주세요. (입력 후 Enter를 두 번 누르세요)", "blue")
            
            # 사용자에게 입력을 요청. 대화형이 아닐 경우 EOFError가 발생할 수 있습니다.
            # Python 2/3 호환성 문제가 있을 수 있으나, Python 3 환경에서는 builtins.input 사용
            
            # 🚨 [핵심 수정]: 비대화형 환경에서 즉시 감지하여 건너뛰도록 처리
            if not sys.stdin.isatty():
                summary = "⚠️ 비대화형 환경(자동 실행)이 감지되어 피드백 수집을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "warning", "summary": summary}
                
            # 표준 입력에서 피드백을 받습니다.
            feedback = builtins.input(">> 피드백 입력: ") 
            self.progress(50)

            # 2. 내용 유효성 검사
            if not feedback or not feedback.strip():
                summary = "⚠️ 입력된 내용이 없어 피드백 저장을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "warning", "summary": summary}

            # 3. 파일 저장
            os.makedirs(self.feedback_dir, exist_ok=True)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 피드백 내용에 줄 바꿈이 포함될 수 있으므로, .strip()된 내용을 저장합니다.
            entry = f"[{now}] {feedback.strip()}\n"

            with open(self.feedback_file, "a", encoding="utf-8") as f:
                f.write(entry)

            summary = f"✅ 피드백 저장 완료: {os.path.basename(self.feedback_file)}에 기록되었습니다."
            log(summary, "lime")
            self.progress(100)
            
            return {"status": "success", "summary": summary}
            
        except EOFError:
            # 보통 sys.stdin.isatty()에서 걸러지지만, 만약을 대비하여 유지
            error_message = "❌ 피드백 수집 실패: 입력 스트림이 닫혔습니다. (비대화형 환경)"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 피드백 수집 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}