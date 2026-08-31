from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 네트워크 프로파일 점검 (NetworkProfile) - 필수 속성 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os

class NetworkProfilePlugin(PCButlerPlugin):
    """
    현재 활성화된 네트워크 프로파일의 유형(개인/공용)을 점검합니다.
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "NetworkProfile"
    description = "현재 활성화된 네트워크 프로파일의 보안 설정 상태를 점검합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # PowerShell을 사용하여 네트워크 프로파일 정보 확인
            ps_script = "Get-NetConnectionProfile | Select-Object Name, NetworkCategory | ConvertTo-Json -Compress"
            
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='cp949', 
                errors='ignore',
                check=False,
                timeout=10 
            )
            
            output = result.stdout.strip()
            
            if not output:
                summary = "네트워크 프로파일 정보를 가져오지 못했습니다. (연결 확인 필요)"
                self.logger(f"  -> ❌ {summary}", "red")
                return {"status": "error", "summary": summary}

            data = []
            try:
                import json
                if output.startswith('['):
                    data = json.loads(output)
                else:
                    data = [json.loads(output)]
            except json.JSONDecodeError:
                summary = "네트워크 프로파일 정보 JSON 파싱 실패."
                self.logger(f"  -> ❌ {summary}", "red")
                return {"status": "error", "summary": summary}

            self.progress(50)
            
            warning_profiles = []
            
            for profile in data:
                category = profile.get('NetworkCategory')
                name = profile.get('Name', 'Unknown')
                
                if category == 2: # 2는 Public(공용)을 의미 (가장 안전함)
                    self.logger(f"  -> ✅ 프로파일 '{name}' : 공용 (양호)", "lime")
                elif category == 1: # 1은 Private(개인)을 의미 (가정/사무실, 보안 수준 중간)
                    self.logger(f"  -> ⚠️ 프로파일 '{name}' : 개인 (주의)", "yellow")
                    warning_profiles.append(name)
                elif category == 0: # 0은 DomainAuthenticated(도메인)
                    self.logger(f"  -> ✅ 프로파일 '{name}' : 도메인 (양호)", "lime")
                else:
                    self.logger(f"  -> ℹ️ 프로파일 '{name}' : 알 수 없는 카테고리 ({category})", "gray")

            self.progress(100)
            
            if warning_profiles:
                summary = f"⚠️ 활성 네트워크 프로파일 중 {len(warning_profiles)}개가 '개인'으로 설정되어 있습니다. 공용 환경에서는 '공용'으로 변경하는 것이 안전합니다."
                status = "warning"
            else:
                summary = "✅ 모든 활성 네트워크 프로파일 상태 양호 (개인/도메인/공용으로 명확히 분류됨)."
                status = "success"

            return {"status": status, "summary": summary, "details": data}

        except Exception as e:
            error_message = f"❌ [오류] 네트워크 프로파일 점검 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}