from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 플러그인 목록 위젯 (PluginListWidget) - 로드 오류 최종 해결
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
# 🚨 [핵심 수정]: No module named 'diagnosis_logger' 오류를 해결하기 위해 
# 해당 임포트 구문은 이 파일에서 완전히 제거되어야 합니다.

class PluginListWidget(PCButlerPlugin):
    """
    (GUI 전용: 콘솔에서는 아무 작업도 수행하지 않는 더미 플러그인)
    """
    # 필수 속성
    plugin_name = "PluginListWidget"
    description = "(GUI 전용) 플러그인 목록을 표시하는 위젯입니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        # 부모 클래스의 run을 호출하여 self.logger와 self.progress를 초기화합니다.
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        # 플러그인 목록 위젯은 실행 대상에서 제외되는 더미이므로 간단한 로그만 남깁니다.
        summary = f"'{self.name}'은 GUI 전용 위젯이므로 콘솔에서는 작업을 수행하지 않습니다."
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")
        self.logger(f"  -> ℹ️ {summary}", "gray")
        
        self.progress(100)
            
        return {"status": "success", "summary": summary}