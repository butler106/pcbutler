from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: Butler 자체 업데이트 (SelfUpdate) - 최종 구조 통일 및 표준화
# - execute_plugin() 제거 및 run() 메서드에 로직 통합
# - 모든 print()를 self.logger()로 교체 및 self.progress() 호출 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import json
import urllib.request
import shutil
from datetime import datetime
from urllib.parse import urlparse
import time # 진행률 업데이트를 위한 시간 함수 추가

class SelfUpdatePlugin(PCButlerPlugin):
    """
    GitHub 서버에서 최신 버전을 확인하고 백업 후 자동으로 업데이트합니다.
    """
    plugin_name = "Butler 자체 업데이트"
    description = "GitHub 서버에서 최신 버전을 확인하고 백업 후 자동으로 업데이트합니다."

    VERSION_FILE = "version_info.json"
    CONFIG_FILE = "user_config.json"
    AUTO_UPDATE_KEY = "auto_update_enabled"
    REMOTE_URL_KEY = "update_server_url"
    
    # 🚨 [표준] __init__ 구조 통일
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # BASE_DIR 설정
        self.base_dir = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = os.path.join(self.base_dir, "config")
        self.backup_dir = os.path.join(self.base_dir, "backup", datetime.now().strftime('%Y%m%d_%H%M%S'))


    # --- Helper Methods ---

    def _get_local_version(self):
        """로컬에 저장된 현재 버전을 읽어옵니다."""
        version_path = os.path.join(self.config_dir, self.VERSION_FILE)
        try:
            with open(version_path, 'r', encoding='utf-8') as f:
                return json.load(f).get('version', '0.0.0')
        except:
            return '0.0.0'

    def _get_remote_version_info(self, url):
        """원격 서버에서 최신 버전 정보 및 파일 목록을 가져옵니다."""
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.logger(f"❌ 원격 서버 접속 실패 ({url}): {e}", "red")
            return None

    def _download_and_replace(self, file_list, remote_version):
        """파일 목록을 다운로드하고 기존 파일을 백업 후 교체합니다."""
        log = self.logger
        total_files = len(file_list)
        progress_range = 80 - 20 # 20%에서 80% 사이

        # 백업 디렉토리 생성
        os.makedirs(self.backup_dir, exist_ok=True)
        
        success_count = 0
        
        for i, file_info in enumerate(file_list):
            remote_path = file_info.get('remote')
            local_path = file_info.get('local')
            
            if not remote_path or not local_path:
                continue

            # 로컬 최종 경로와 임시 다운로드 경로 설정
            final_dest_path = os.path.join(self.base_dir, local_path)
            temp_file_path = final_dest_path + ".tmp_download"
            
            log(f"\n🔄 파일 처리 시작: {local_path}", "white")

            # 1. 파일 다운로드
            try:
                log(f"  -> 다운로드 시도: {remote_path}", "gray")
                urllib.request.urlretrieve(remote_path, temp_file_path)
                log("  -> 다운로드 완료.", "white")
            except Exception as e:
                log(f"❌ 다운로드 실패 ({remote_path}): {e}", "red")
                continue
                
            # 2. 기존 파일 백업
            if os.path.exists(final_dest_path):
                backup_file_path = os.path.join(self.backup_dir, os.path.basename(local_path))
                shutil.copy2(final_dest_path, backup_file_path)
                log(f"  -> 백업 완료: {os.path.basename(backup_file_path)}", "gray")
            else:
                log("  -> 기존 파일 없음. 백업 건너뜀.", "gray")

            # 3. 파일 교체
            os.makedirs(os.path.dirname(final_dest_path), exist_ok=True)
            os.replace(temp_file_path, final_dest_path)
            log(f"  -> 교체 완료: {local_path}", "lime")
            success_count += 1

            # 진행률 업데이트
            self.progress(20 + int((i + 1) / total_files * progress_range))
            
        # 4. 버전 파일 업데이트
        local_version_path = os.path.join(self.config_dir, self.VERSION_FILE)
        if success_count > 0:
            log(f"\n  -> 버전 파일 업데이트: {local_version_path}", "white")
            with open(local_version_path, "w", encoding="utf-8") as f:
                json.dump({"version": remote_version}, f, indent=2, ensure_ascii=False)
        
        return success_count


    # 🚨 [핵심] run 메서드에 로직 통합
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)
        
        # 1. 설정값 확인
        remote_url = self.settings.get(self.REMOTE_URL_KEY)
        if not remote_url:
            summary = "❌ 업데이트 서버 URL이 config.ini에 정의되어 있지 않아 업데이트를 건너뜁니다."
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}

        # 2. 로컬 및 원격 버전 확인
        local_version = self._get_local_version()
        log(f"  -> 로컬 현재 버전: {local_version}", "white")

        remote_info = self._get_remote_version_info(remote_url)
        if not remote_info:
            summary = "❌ 원격 서버 정보를 가져오는 데 실패하여 업데이트를 건너뜁니다."
            self.progress(100)
            return {"status": "error", "summary": summary}
            
        remote_version = remote_info.get('version')
        file_list = remote_info.get('files', [])

        log(f"  -> 원격 최신 버전: {remote_version}", "white")
        self.progress(20)

        if remote_version <= local_version:
            summary = f"✅ 현재 버전 ({local_version})이 최신 버전({remote_version})입니다. 업데이트가 필요 없습니다."
            log(summary, "lime")
            self.progress(100)
            return {"status": "success", "summary": summary}

        log(f"⚠️ 새 버전({remote_version})이 확인되었습니다. 업데이트를 시작합니다.", "yellow")

        # 3. 파일 다운로드 및 교체 실행
        try:
            success_count = self._download_and_replace(file_list, remote_version)
        except Exception as e:
            error_message = f"❌ 파일 다운로드/교체 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}


        # 4. 최종 결과 반환
        if success_count > 0:
            summary = f"✅ PC Butler가 **v{remote_version}**으로 성공적으로 업데이트되었습니다. (총 {success_count}개 파일 교체)"
            log(summary, "lime")
            final_status = "success"
        else:
            summary = "⚠️ 업데이트가 필요하지만, 파일을 다운로드하거나 교체하는 데 실패했습니다. 로그를 확인하십시오."
            log(summary, "yellow")
            final_status = "warning"
            
        self.progress(100)
        
        return {"status": final_status, "summary": summary}