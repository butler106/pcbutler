from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 플러그인 포함 여부 확인 (PluginInclusionChecker) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
# 이 플러그인은 다른 플러그인이 로드되었는지 확인하는 내부 로직용으로 보임.
class PluginInclusionChecker(PCButlerPlugin):
    """
    (내부용) 모든 플러그인 파일이 목록에 포함되어 있는지 확인합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "PluginInclusion"
    description = "(내부용) 플러그인 로드 무결성 검사기입니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다. (더미 로직)", "cyan")
        
        # 실제 로직은 모든 파일 로드 후 실행 단계에서 체크됨
        self.progress(100)
        summary = "플러그인 포함 여부 검사 완료. 로드 실패가 없다면 정상입니다."
        return {"status": "success", "summary": summary}