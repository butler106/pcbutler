from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 기본 글꼴 상태 점검 (FontCheck) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import os

class FontCheckPlugin(PCButlerPlugin):
    """
    Windows 기본 글꼴(예: 맑은 고딕)의 존재 여부를 확인합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "Fontcheck"
    description = "Windows 필수 글꼴의 존재 여부를 확인합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}

        self.progress(10)
        
        # Windows Fonts 폴더 경로
        font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
        
        # 필수 글꼴 목록 (예시)
        required_fonts = {
            "맑은 고딕": "malgun.ttf",
            "Arial": "arial.ttf",
            "Times New Roman": "times.ttf"
        }
        
        missing_fonts = []
        
        for i, (font_name, file_name) in enumerate(required_fonts.items()):
            font_path = os.path.join(font_dir, file_name)
            if not os.path.exists(font_path):
                missing_fonts.append(font_name)
                self.logger(f"  -> ❌ 필수 글꼴 누락: {font_name} ({file_name})", "red")
            else:
                self.logger(f"  -> ✅ 글꼴 확인: {font_name} 존재.", "lime")
                
            self.progress(10 + int(80 * (i + 1) / len(required_fonts)))

        if missing_fonts:
            summary = f"❌ {len(missing_fonts)}개의 필수 글꼴이 누락되었습니다. ({', '.join(missing_fonts)})"
            status = "error"
        else:
            summary = f"✅ 모든 필수 글꼴 ({len(required_fonts)}개) 존재 확인. 상태 양호."
            status = "success"

        self.logger(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime" if status == "success" else "red")
        self.progress(100)
            
        return {"status": status, "summary": summary, "details": missing_fonts}