from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 브라우저 기록 점검 (BrowserHistoryCheck) - [개선 완료]
# - 1. 클래스명 충돌을 방지하기 위해 BrowserHistoryPlugin으로 변경했습니다.
# - 2. Firefox의 경우, 실제 프로필 폴더를 찾아 places.sqlite 파일 존재 여부를 확인하도록 로직을 개선했습니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os

class BrowserHistoryPlugin(PCButlerPlugin): # <-- 클래스명 변경
    """
    주요 브라우저의 기록 파일 존재 여부를 확인합니다. (실제 기록 내용은 확인하지 않음)
    """
    # 🚨 [수정] 필수 속성 추가
    plugin_name = "BrowserHistoryCheck" # <-- 플러그인 이름 변경
    description = "Chrome, Edge, Firefox 등 주요 브라우저의 기록 파일 존재 여부를 확인합니다."
    
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

        appdata = os.environ.get('LOCALAPPDATA')
        
        # 1. Chrome, Edge는 History 파일 경로를 직접 지정
        history_files = {
            "Chrome": os.path.join(appdata, r'Google\Chrome\User Data\Default\History'),
            "Edge": os.path.join(appdata, r'Microsoft\Edge\User Data\Default\History'),
        }

        found_browsers = []
        
        # 2. Chrome 및 Edge 기록 파일 존재 확인
        for i, (name, path) in enumerate(history_files.items()):
            if os.path.exists(path):
                found_browsers.append(name)
                self.logger(f"  -> ✅ 브라우저 기록 파일 발견: {name}", "lime")
            else:
                self.logger(f"  -> ℹ️ 브라우저 기록 파일 미발견: {name}", "gray")
            self.progress(10 + int(40 * (i + 1) / len(history_files)))
        
        # 3. Firefox 기록 파일 존재 확인 (프로필 폴더 검색 로직)
        self.progress(50)
        firefox_profiles_path = os.path.join(appdata, r'Mozilla\Firefox\Profiles')
        found_firefox_history = False
        
        if os.path.exists(firefox_profiles_path):
            self.logger(f"  -> 📂 Firefox 프로필 경로 확인: {firefox_profiles_path}", "gray")
            
            # Profiles 폴더 내의 모든 서브 디렉토리 (프로필) 확인
            for profile_dir in os.listdir(firefox_profiles_path):
                full_profile_path = os.path.join(firefox_profiles_path, profile_dir)
                # 디렉토리이고, 실제 기록 파일(places.sqlite)을 포함하는지 확인
                if os.path.isdir(full_profile_path):
                    history_file = os.path.join(full_profile_path, 'places.sqlite')
                    if os.path.exists(history_file):
                        found_browsers.append("Firefox")
                        self.logger(f"  -> ✅ 브라우저 기록 파일 발견: Firefox (프로필: {profile_dir})", "lime")
                        found_firefox_history = True
                        break # 하나의 기록만 찾으면 충분하므로 종료
        
        if not found_firefox_history:
            self.logger(f"  -> ℹ️ 브라우저 기록 파일 미발견: Firefox", "gray")
        
        self.progress(80)

        # 4. 최종 결과 요약 및 반환
        count = len(found_browsers)
        if count == 0:
            status = "success" # 기록이 없는 것은 긍정적일 수 있음
            summary = "주요 브라우저 기록 파일이 발견되지 않았습니다. (상태 양호)"
            self.logger(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime")
        else:
            status = "warning"
            summary = f"총 {count}개의 브라우저 기록 파일이 발견되었습니다: {', '.join(found_browsers)}. (보안 점검 권장)"
            self.logger(f"\n⚠️ '{self.name}' 작업을 완료했습니다. ({summary})", "yellow")
            
        self.progress(100)
        
        return {"status": status, "summary": summary}