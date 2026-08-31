from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 기관별 진단 템플릿 적용 (OrgTemplate) - 완벽한 버전
# - 기관별 JSON 템플릿을 읽어 user_config.json에 반영하는 실제 기능 구현
# ==============================================================================
from plugin_base import PCButlerPlugin
import json
import os
from json.decoder import JSONDecodeError # JSON 오류 처리를 위해 추가

class OrgTemplatePlugin(PCButlerPlugin):
    """
    기관별로 미리 정의된 진단 항목 템플릿(org_template.json)을 읽어 
    user_config.json에 적용합니다.
    """
    plugin_name = "OrgTemplate" # 명확한 플러그인 이름
    description = "기관별로 미리 정의된 진단 항목 템플릿을 적용하여 설정 파일을 갱신합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (템플릿 적용)", "cyan")
        self.progress(10)

        # BASE_DIR을 settings에서 가져와 config 경로를 구성합니다.
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
        
        try:
            log("🏫 기관 템플릿 적용 시작...", "white")
            
            config_dir = os.path.join(base_path, "config")
            template_file = os.path.join(config_dir, "org_template.json")
            user_config_file = os.path.join(config_dir, "user_config.json")
            
            # config 디렉토리가 없으면 생성합니다.
            os.makedirs(config_dir, exist_ok=True)
            self.progress(30)

            # --------------------------------------------------------
            # 1. 템플릿 파일 존재 여부 확인 (경고로 흐름 유지)
            # --------------------------------------------------------
            if not os.path.exists(template_file):
                summary = f"⚠️ 기관 템플릿 파일이 없습니다: {os.path.basename(template_file)} (작업 건너뜀)"
                log(summary, "yellow")
                self.progress(100) # 완료 처리
                # ✅ [완벽한 흐름 유지] 파일이 없어도 Warning 반환
                return {"status": "warning", "summary": summary}

            # --------------------------------------------------------
            # 2. 템플릿 파일 읽기 및 유효성 검사 (JSONDecodeError 명시적 처리)
            # --------------------------------------------------------
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    template = json.load(f)
            except JSONDecodeError as e:
                error_message = f"❌ 템플릿 파일({os.path.basename(template_file)})이 JSON 형식이 아닙니다: {e}"
                log(error_message, "red")
                self.progress(100)
                # 🚨 [완벽한 오류 처리] JSON 형식이 깨진 경우 Error 반환
                return {"status": "error", "summary": error_message}
            
            # 템플릿 데이터 추출
            org_name = template.get("organization", "Default Organization")
            enabled_plugins = template.get("enabled_plugins", [])
            
            log(f"  -> 템플릿 확인: {org_name} (활성화 플러그인 수: {len(enabled_plugins)})", "gray")
            self.progress(70)

            # --------------------------------------------------------
            # 3. user_config.json에 설정 반영
            # --------------------------------------------------------
            user_config = {
                "description": f"{org_name} 진단 설정 (템플릿 적용됨)",
                "enabled_plugins": enabled_plugins
            }
            
            # user_config.json 파일에 설정 반영
            with open(user_config_file, "w", encoding="utf-8") as f:
                json.dump(user_config, f, indent=4, ensure_ascii=False)

            summary = f"✅ {org_name} 템플릿 적용 완료 → {os.path.basename(user_config_file)} 갱신됨"
            log(summary, "lime")
            
            self.progress(100) # 완료 처리
            return {"status": "success", "summary": summary}
            
        except Exception as e:
            # 예상치 못한 기타 I/O 오류 또는 권한 오류 처리
            error_message = f"❌ 기관 템플릿 적용 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}