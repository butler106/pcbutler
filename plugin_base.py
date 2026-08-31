# ==============================================================================
# 🐍 PC Butler: plugin_base.py (기반 클래스) - GUI 안정화 버전
# [핵심 수정] 1. run() 메서드에서 불필요한 경고 메시지 제거.
#            2. _save_result_to_file: main.py에서 주입한 절대 경로 사용.
# ==============================================================================
import os
import json
from typing import Dict, Any, Callable, Optional, Union, List

class PCButlerPlugin:
    plugin_name = "BasePlugin" 
    description = "기본 플러그인 템플릿"
    version = "1.0.3" 

    def __init__(self, analysis_id: str, settings: Any):
        self.analysis_id = analysis_id
        self.settings = settings
        
        # 기본 로깅/진행률 함수 설정 (Mock 함수)
        self.logger: Callable[[str, Optional[str]], None] = lambda msg, color=None: print(msg)
        self.progress: Callable[[int], None] = lambda pct: None

    # run 시그니처는 통일하되, 하위 클래스에서 super().run() 호출 시 불필요한 경고 출력을 막습니다.
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # main.py에서 전달된 실제 콜백 함수로 Mock 함수 대체
        if logger: self.logger = logger
        if progress: self.progress = progress
        
        # 🚨 불필요한 경고 메시지 제거 (하위 플러그인에서 super().run 호출 시 중복 경고 방지)
        # self.logger(f"⚠️ '{self.plugin_name}' 플러그인이 run() 메서드를 구현하지 않았습니다.", "yellow")
        
        # run이 오버라이드되지 않은 경우에만 이 결과를 반환합니다.
        return {"status": "base_called", "summary": f"'{self.plugin_name}' 플러그인 기본 run()이 호출됨"}


    def _save_result_to_file(self, result: dict):
        """
        플러그인 실행 결과를 JSON 파일로 reports 폴더에 저장합니다.
        settings['REPORT_DIR_FINAL'] 절대 경로를 사용합니다.
        """
        plugin_name = self.__class__.plugin_name
        
        try:
            # ✅ CRITICAL FIX: main.py에서 주입한 절대 경로 'REPORT_DIR_FINAL' 사용
            report_dir = self.settings.get('REPORT_DIR_FINAL') 
            
            if not report_dir:
                self.logger("❌ 보고서 저장 경로가 불명확합니다. 파일 저장을 건너뜁니다.", "red")
                return 
                
            os.makedirs(report_dir, exist_ok=True)
            
            filename = f"{plugin_name}_{self.analysis_id}.json"
            filepath = os.path.join(report_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            
            self.logger(f"✅ 결과 저장 완료: {filename}", "gray")
            
        except Exception as e:
            self.logger(f"❌ JSON 결과 저장 실패: {plugin_name} ({type(e).__name__}: {e})", "red")