from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: Butler 버전 업데이트 확인 (UpdateCheck) - 최종 구현 (완벽한 예외 처리 포함)
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import json
import urllib.request 
import urllib.error 

class UpdateCheckPlugin(PCButlerPlugin):
    plugin_name = "업데이트 확인"
    description = "현재 Butler 버전과 서버 버전을 비교하여 업데이트 필요 여부를 안내합니다."
    
    REMOTE_VERSION_URL = "https://example.com/pcbutler/version_info.json" 

    def _get_remote_version(self, log):
        """원격 서버에서 버전 정보 가져오기 (더미 로직 대체)"""
        try:
            log("  -> 🌐 서버에서 최신 버전 정보 다운로드 시도 중...", "gray")
            with urllib.request.urlopen(self.REMOTE_VERSION_URL, timeout=10) as response:
                remote_data = json.loads(response.read().decode('utf-8'))
                return remote_data.get("version", "v000").strip()
        except urllib.error.URLError as e:
            # 네트워크 오류는 여기서 처리하고 None을 반환
            log(f"❌ 네트워크 오류: 서버에 연결할 수 없습니다. ({e.reason})", "red")
            return None
        except Exception as e:
            # 기타 오류 발생 시 None 반환
            log(f"❌ 원격 버전 확인 중 오류 발생: {type(e).__name__} - {e}", "red")
            return None
    
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        # BASE_DIR 설정
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_version_file = os.path.join(base_path, "config", "version_info.json") 
        
        local_version = "N/A"
        
        # 🚨 [최종 수정] 전체 로직을 하나의 try 블록으로 감싸 예외를 처리합니다.
        try:
            # 1. 로컬 버전 로드
            try:
                with open(local_version_file, "r", encoding='utf-8') as f:
                    version_info = json.load(f)
                local_version = version_info.get("version", "v000").strip()
                self.progress(30)
            except FileNotFoundError:
                log(f"❌ 로컬 버전 파일({os.path.basename(local_version_file)})을 찾을 수 없습니다. 기본값 'v000'으로 진행합니다.", "red")
                local_version = "v000"
                self.progress(30)
            except Exception:
                # 파일 로드 중 기타 오류 처리
                local_version = "v000"
                self.progress(30)


            # 2. 원격 버전 확인 (네트워크 통신)
            server_version = self._get_remote_version(log)
            if server_version is None:
                # _get_remote_version에서 이미 오류 로깅됨
                summary = "❌ 업데이트 확인 실패: 서버 연결 또는 버전 정보 로드에 실패했습니다."
                self.progress(100)
                # 🚨 [주의] 이 return은 _get_remote_version에서 네트워크 오류 발생 시 즉시 반환
                return {"status": "error", "summary": summary} 
                
            log(f"📦 현재 로컬 버전: {local_version}", "white")
            log(f"🌐 서버 최신 버전: {server_version}", "white")
            self.progress(60)

            # 3. 버전 비교
            if local_version == server_version:
                summary = f"✅ 최신 버전입니다: {local_version}"
                log(summary, "lime")
                final_status = "success"
            else:
                summary = f"⚠️ 업데이트 필요: 현재 {local_version} → 최신 {server_version}. 업데이트 제안 확인을 권장합니다."
                log(summary, "yellow")
                final_status = "warning"
            
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": summary}
            
        # 4. 최상위 예외 처리 로직 (생략되었던 부분)
        except json.JSONDecodeError:
            error_message = f"❌ 로컬 버전 정보 파일({os.path.basename(local_version_file)}) 내용이 유효한 JSON 형식이 아닙니다."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 업데이트 확인 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}