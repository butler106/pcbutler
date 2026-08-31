from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 자체 무결성 검사 (Selfcheck) - [모든 알려진 오류 해결 최종 버전]
# - 🚨 CRITICAL FIX: NameError 및 TypeError: 'Event' object is not callable 해결
# ==============================================================================
import os
import sys 
import json 
from datetime import datetime
import time 

# 🚨 CRITICAL FIX 1: ModuleNotFoundError 해결을 위한 경로 추가
# (main.py의 BASE_DIR 설정을 신뢰하고 플러그인 폴더에 있다면 생략 가능)
try:
    if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
except:
    pass

from plugin_base import PCButlerPlugin 

class SelfCheckPlugin(PCButlerPlugin):
    plugin_name = "자체 무결성 검사"
    description = "PC Butler 프로그램의 필수 폴더 및 파일 존재 여부를 확인합니다."
    version = "2.3" # 최종 버전
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        
        # 🚨 CRITICAL FIX 2: super().run 호출로 log/progress/stop_check 초기화
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        try:
            log(f"🔍 '{self.name}' 작업을 시작합니다. (필수 파일/폴더 확인)", "cyan")
            
            base_dir = kwargs.get("plugin_base_dir", os.path.dirname(os.path.abspath(__file__)))
            # base_dir은 plugins 폴더를 가리킨다고 가정하고 상위 폴더를 Root로 설정
            pcbutler_root = os.path.dirname(base_dir) 

            # 검사 대상 목록 정의
            CHECK_LIST = {
                "plugins 폴더": {"type": "폴더", "path": base_dir},
                "reports 폴더": {"type": "폴더", "path": os.path.join(pcbutler_root, "reports")},
                "config.ini": {"type": "파일", "path": os.path.join(pcbutler_root, "config.ini")},
                "main.py": {"type": "파일", "path": os.path.join(pcbutler_root, "main.py")},
                # 🚨 FIX (2026-08-31): plugin_base.py는 plugins 폴더가 아니라 프로젝트 루트에
                # 있으므로, base_dir(=plugins 폴더)가 아닌 pcbutler_root 기준으로 확인해야 한다.
                # 기존 코드는 base_dir 기준으로 확인해 실제 실행 시 항상 "누락"으로 오탐했다.
                "plugin_base.py": {"type": "파일", "path": os.path.join(pcbutler_root, "plugin_base.py")},
            }
            
            results = {}
            error_count = 0
            total_checks = len(CHECK_LIST)

            for i, (name, item) in enumerate(CHECK_LIST.items()):
                path = item['path']
                type_str = item['type']
                is_valid = False

                if type_str == "폴더":
                    is_valid = os.path.isdir(path)
                elif type_str == "파일":
                    is_valid = os.path.isfile(path)

                results[name] = {"type": type_str, "path": path, "status": "OK" if is_valid else "MISSING"}
                
                if not is_valid:
                    log(f"  -> ❌ 누락: {type_str} **{name}** ({path})", "red")
                    error_count += 1
                else:
                    log(f"  -> ✅ 확인: {type_str} **{name}**", "lime")
                    
                self.progress(10 + int(80 * (i + 1) / total_checks))
                
                # 🚨 CRITICAL FIX 3: stop_check는 함수이므로 '호출'해야 합니다.
                # 'TypeError: 'Event' object is not callable' 방지
                if stop_check and stop_check():
                    final_summary = "⚠️ 사용자 요청으로 무결성 검사 중단됨."
                    return {"status": "warning", "summary": final_summary}
            
            if error_count == 0:
                overall_status = "success"
                final_summary = "✅ PC Butler 프로그램의 필수 파일 및 폴더 무결성 검사를 통과했습니다."
            else:
                overall_status = "error"
                final_summary = f"❌ PC Butler 프로그램의 필수 파일/폴더 중 **총 {error_count}개**가 누락되었습니다. 프로그램 재설치가 필요할 수 있습니다."

            log(f"\n✅ '{self.name}' 작업을 완료했습니다. ({final_summary})", "lime" if overall_status == "success" else "red")
            self.progress(100)
            
            return {"status": overall_status, "summary": final_summary, "details": {"checks": results}}

        except Exception as e:
            error_message = f"플러그인 전체 실행 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": error_message}