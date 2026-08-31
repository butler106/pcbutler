from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_configlock.py
# 플러그인: 설정 파일 잠금 (v1.1 - NoneType 오류 및 경로 수정)
import os

class ConfigLockPlugin(PCButlerPlugin):
    plugin_name = "설정 잠금"
    description = "user_config.json 및 템플릿 파일을 잠금하여 무단 변경을 방지합니다. (읽기 전용 설정)"

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # BASE_DIR을 settings에서 가져와 config 경로를 구성합니다.
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        config_files = [
            os.path.join(base_path, "config", "user_config.json"),
            os.path.join(base_path, "config", "org_template.json"),
            os.path.join(base_path, "config", "user_profile.json")
        ]
        
        locked_count = 0
        
        try:
            log("🔒 설정 파일 잠금(읽기 전용) 처리 중...", "white")
            
            for i, fpath in enumerate(config_files):
                self.progress(10 + int(80 * (i / len(config_files))))
                
                if os.path.exists(fpath):
                    # 0o444는 소유자, 그룹, 기타 모두에게 읽기 전용 권한을 부여합니다.
                    # Windows에서는 읽기 전용 속성을 설정합니다.
                    os.chmod(fpath, 0o444)
                    log(f"  → ✅ 잠금됨: {os.path.basename(fpath)}", "gray")
                    locked_count += 1
                else:
                    log(f"  → ⚠️ 파일 없음: {os.path.basename(fpath)}", "yellow")

            summary = f"✅ 설정 잠금 완료. 총 {locked_count}개 파일이 읽기 전용으로 설정되었습니다."
            log(summary, "lime")
            self.progress(100)
            
            # 🚨 [필수] Success 반환
            return {"status": "success", "summary": summary}
            
        except Exception as e:
            error_message = f"❌ 설정 잠금 실패: 권한 문제 또는 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경 (불필요한 return 제거)
    def plugin_stop(self):
        self.logger("🛑 설정 잠금 플러그인 종료됨", "gray")
        pass