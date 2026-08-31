from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 최종 요약 (영문) (StatSummaryEn) - 필수 속성 추가 및 영문 통일
# ==============================================================================
from plugin_base import PCButlerPlugin
import os

class StatSummaryEnPlugin(PCButlerPlugin):
    """
    모든 플러그인 결과를 취합하여 최종 요약 통계를 생성합니다. (영문 버전)
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "StatSummaryEn"
    description = "Generates the final summary statistics. (English)" # 영문 설명으로 변경
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        # 🌟 [수정] 로그 메시지를 영문으로 변경
        self.logger(f"🔍 '{self.name}' job started. (Dummy Logic)", "cyan") 

        self.progress(100)
        # 🌟 [수정] 요약 메시지를 영문으로 변경
        summary = "English final summary generation is currently set to dummy mode for the console version."
        return {"status": "success", "summary": summary}