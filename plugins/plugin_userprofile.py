from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_userprofile.py
# 플러그인: 사용자 프로파일 기반 진단 구성 (최종 표준화 버전)
import json
import os
import sys

class UserProfilePlugin(PCButlerPlugin):
    plugin_name = "사용자 프로파일 적용"
    description = "사용자별로 정의된 진단 항목 구성을 자동 적용합니다."

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (user_profile.json 로드)", "cyan")
        self.progress(10)

        # 1. BASE_DIR 기반으로 설정 파일 경로 구성
        base_path = self.settings.get(
            "BASE_DIR", 
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 폴백 경로
        )
        config_dir = os.path.join(base_path, "config")
        profile_file = os.path.join(config_dir, "user_profile.json")
        user_config_file = os.path.join(config_dir, "user_config.json") # 최종 사용자 설정 파일

        try:
            log(f"👤 사용자 프로파일 파일 확인 중: {os.path.basename(profile_file)}", "white")
            self.progress(30)
            
            # 2. 프로파일 파일 로드
            if not os.path.exists(profile_file):
                summary = "⚠️ 사용자 프로파일 파일(user_profile.json)이 존재하지 않습니다. 프로파일 설정을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "WARNING", "summary": summary}

            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_config = json.load(f)
            
            self.progress(50)

            # 3. 프로파일에서 실행 플러그인 목록 추출
            # 'user_name' 또는 'current_user'와 같은 키가 있을 수 있으나, 여기서는 목록만 추출
            user_name = profile_config.get("user_name", os.getlogin() if os.name == 'nt' else "DefaultUser")
            enabled_plugins = profile_config.get("enabled_plugins", [])
            
            log(f"✅ 프로파일 '{user_name}' 로드 성공. 설정된 플러그인: {len(enabled_plugins)}개", "lime")
            self.progress(70)

            # 4. user_config.json에 프로파일 내용을 반영
            user_config = {
                "description": f"{user_name} 사용자 진단 설정",
                "enabled_plugins": enabled_plugins
            }

            os.makedirs(config_dir, exist_ok=True)
            with open(user_config_file, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)
            
            log(f"✅ 사용자 프로파일 '{user_name}' 적용 완료. (→ {os.path.basename(user_config_file)} 업데이트)", "lime")

            summary = f"✅ 사용자 프로파일 '{user_name}' 적용 완료. {len(enabled_plugins)}개 플러그인 실행 설정됨."
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": "SUCCESS", "summary": summary, "details": enabled_plugins}
            
        except json.JSONDecodeError:
            error_message = f"❌ 프로파일 파일({os.path.basename(profile_file)}) 내용이 유효한 JSON 형식이 아닙니다."
            log(error_message, "red")
            self.progress(100)
            return {"status": "ERROR", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 사용자 프로파일 적용 중 예상치 못한 오류 발생: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] 최종 결과를 딕셔너리 형태로 반환
            return {"status": "ERROR", "summary": error_message}