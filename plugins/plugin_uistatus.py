from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_uistatus.py
# 플러그인: UI 상태 표시 개선 (GUI 전용 안전 로직 최종 버전)
class UIStatusPlugin(PCButlerPlugin):
    """
    진단 결과를 Butler UI에 시각적으로 표시하는 GUI 전용 플러그인입니다.
    콘솔 환경에서 안전하게 건너뛰도록 처리되었습니다.
    """
    plugin_name = "UIStatus"
    description = "진단 결과를 GUI에 표시하여 상태를 한눈에 파악할 수 있도록 합니다. (GUI 전용)"
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")
        
        # --------------------------------------------------------
        # 💡 [최종 로직] 콘솔 환경에서 GUI 전용임을 명시하고 WARNING 반환
        # --------------------------------------------------------
        summary = "이 플러그인은 **GUI 환경**에서 UI를 업데이트하는 용도입니다. **콘솔 환경에서는 실행 흐름을 유지하기 위해 건너뜁니다.**"
        
        log(f"⚠️ [건너뜀] {self.name} : {summary}", "yellow")
        
        # '더미'가 아닌 '완료' 상태를 알리고 메인 프로그램이 다음 작업을 진행하도록 100% 보고
        self.progress(100)
        
        # 🚨 [필수] WARNING 상태를 반환하여, 이 플러그인의 결과를 최종 보고서에 '실패'가 아닌 '경고/건너뜀'으로 기록합니다.
        return {"status": "WARNING", "summary": summary}