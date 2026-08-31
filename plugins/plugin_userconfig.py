from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_userconfig.py
# 플러그인: 사용자 설정 기반 진단 항목 선택 (최종 경로 안정화 및 표준화)
import json
import os
from datetime import datetime

class UserConfigPlugin(PCButlerPlugin):
    plugin_name = "사용자 설정 기반 진단 항목 선택"
    description = "사용자 설정 파일(user_config.json)을 기반으로 진단 항목의 실행 여부를 제어합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (user_config.json 로드)", "cyan")
        self.progress(10)

        # 1. BASE_DIR 기반으로 설정 파일 경로 구성
        # settings에서 BASE_DIR을 가져와 config 경로를 구성합니다. (최종 경로 안정화)
        base_path = self.settings.get(
            "BASE_DIR", 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # BASE_DIR이 없을 때의 폴백 경로
        )
        config_path = os.path.join(base_path, "config", "user_config.json")

        try:
            log(f"⚙️ 사용자 설정 파일 확인 중: {os.path.basename(config_path)}", "white")
            self.progress(30)
            
            # 2. 파일 존재 여부 확인
            if not os.path.exists(config_path):
                summary = "⚠️ 설정 파일이 존재하지 않습니다. → 기본값으로 전체 진단 실행을 가정합니다."
                log(summary, "yellow")
                self.progress(100)
                # 파일이 없으면 WARNING을 반환하고 기본 동작(전체 실행)을 유도합니다.
                return {"status": "WARNING", "summary": summary}

            # 3. 파일 로드 및 'enabled_plugins' 확인
            with open(config_path, 'r', encoding='utf-8') as f:
              config = json.load(f)

            enabled_plugins = config.get("enabled_plugins", [])
            
            self.progress(70)

            if not enabled_plugins:
                 summary = "⚠️ 'enabled_plugins' 항목이 비어 있어 전체 진단 실행을 가정합니다."
                 log(summary, "yellow")
                 final_status = "WARNING"
            else:
                log(f"✅ 사용자 설정에 따라 {len(enabled_plugins)}개 플러그인이 실행됩니다 (main.py에서 제어):", "lime")
                for plugin in enabled_plugins:
                    log(f"  🔹 {plugin}", "gray")
                
                summary = f"✅ 사용자 설정 파일 로드 완료. {len(enabled_plugins)}개 플러그인 실행 예정."
                final_status = "SUCCESS"

            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": summary, "details": enabled_plugins}
            
        except json.JSONDecodeError:
            error_message = f"❌ 설정 파일({os.path.basename(config_path)}) 내용이 유효한 JSON 형식이 아닙니다."
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 사용자 설정 점검 실패: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] 최종 결과를 딕셔너리 형태로 반환
            return {"status": "ERROR", "summary": error_message}