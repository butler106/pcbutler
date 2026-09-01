from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_applyupgrade.py
# Butler 승인 기반 업데이트 적용 플러그인 (v1.3 - NoneType 오류 및 표준 구조 적용)

# -*- coding: utf-8 -*-
import sys
import io
import os
import json
import shutil
from datetime import datetime

# 콘솔 인코딩 문제 방지
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

class ApplyUpgradePlugin(PCButlerPlugin):
    plugin_name = "업데이트 승인 적용"
    description = "승인된 업데이트를 백업 후 실제로 적용하며, 완료 후 관련 파일을 자동 정리합니다."

    PROPOSAL_FILE = "update_proposal.json"
    APPROVAL_FILE = "approval_ui.txt"
    VERSION_FILE = "version_info.json"
    APPLY_LOG = "apply_log.json"

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        # BASE_DIR을 settings에서 가져와 경로를 구성합니다.
        self.base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_dir = os.path.join(self.base_path, "config")
        self.reports_dir = os.path.join(self.base_path, "reports")
        self.update_temp_dir = os.path.join(self.base_path, "update_temp")
        
        # 필요한 기본 폴더는 미리 생성합니다.
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.update_temp_dir, exist_ok=True)

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🛠️ '{self.plugin_name}' 작업을 시작합니다. (v1.3)", "cyan")
        self.progress(10)

        proposal_path = os.path.join(self.config_dir, self.PROPOSAL_FILE)
        approval_path = os.path.join(self.reports_dir, self.APPROVAL_FILE)
        version_path = os.path.join(self.config_dir, self.VERSION_FILE)
        apply_log_path = os.path.join(self.reports_dir, self.APPLY_LOG)

        try:
            # 1. 승인 여부 확인
            if not os.path.exists(approval_path):
                summary = "⚠️ 업데이트 승인 파일(approval_ui.txt)이 없어 적용을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "warning", "summary": summary}

            with open(approval_path, "r", encoding="utf-8") as f:
                approved = f.read().strip().upper() == "APPROVED"
            
            if not approved:
                summary = "⚠️ 사용자 업데이트 승인(APPROVED)이 확인되지 않아 적용을 건너뜁니다."
                log(summary, "yellow")
                self.progress(100)
                return {"status": "warning", "summary": summary}
            
            log("✅ 사용자 업데이트 승인(APPROVED) 확인.", "lime")
            self.progress(20)

            # 2. 업데이트 제안 파일 로드
            if not os.path.exists(proposal_path):
                summary = "❌ 업데이트 제안 파일(update_proposal.json)이 없어 적용에 실패했습니다."
                log(summary, "red")
                self.progress(100)
                return {"status": "error", "summary": summary}
            
            with open(proposal_path, "r", encoding="utf-8") as f:
                proposal_content = json.load(f)
            
            new_version = proposal_content.get("version", "N/A")
            files_to_update = proposal_content.get("files", [])

            log(f"✨ 버전 {new_version} 업데이트 파일을 적용합니다. (총 {len(files_to_update)}개 파일)", "white")
            self.progress(30)
            
            applied_count = 0
            
            # 3. 파일 적용 및 백업
            log("💾 파일 백업 및 적용 중...", "white")
            for i, file_info in enumerate(files_to_update):
                if self.self.stop_event and self.self.stop_event.is_set():
                    summary = "🛑 업데이트 적용 작업이 사용자 요청으로 중단되었습니다."
                    log(summary, "yellow")
                    self.progress(100)
                    return {"status": "warning", "summary": summary}
                    
                self.progress(30 + int(50 * (i / len(files_to_update))))
                
                relative_dest_path = file_info["path"]
                dest_path = os.path.join(self.base_path, relative_dest_path)
                temp_path = os.path.join(self.base_path, file_info["temp_path"]) # update_temp 폴더 내 경로
                
                if not os.path.exists(temp_path):
                    log(f"  -> ⚠️ 임시 파일 없음: {file_info['temp_path']} 적용 실패", "yellow")
                    continue
                    
                # 목적지 폴더 자동 생성
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # 백업
                if os.path.exists(dest_path):
                    backup_dir = os.path.join(self.reports_dir, "backup", datetime.now().strftime("%Y%m%d_%H%M%S"))
                    backup_path = os.path.join(backup_dir, relative_dest_path)
                    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                    shutil.copy2(dest_path, backup_path)
                    log(f"  -> 백업: {os.path.basename(dest_path)}", "gray")
                
                # 적용
                shutil.copy2(temp_path, dest_path)
                log(f"  -> 적용: {os.path.basename(dest_path)}", "gray")
                applied_count += 1
                
            self.progress(80)

            # 4. 버전 정보 업데이트
            if new_version != "N/A":
                current_version_info = {"version": new_version, "applied_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                with open(version_path, "w", encoding="utf-8") as f:
                    json.dump(current_version_info, f, indent=4)
                log(f"➡️ 버전 정보 업데이트 완료: {new_version}", "lime")
                
            # 5. 임시 파일 및 승인 파일 정리
            if os.path.exists(self.update_temp_dir):
                shutil.rmtree(self.update_temp_dir)
                log("🗑️ 임시 업데이트 폴더(update_temp) 정리 완료.", "gray")
            
            if os.path.exists(approval_path):
                os.remove(approval_path)
                log("🗑️ 승인 파일(approval_ui.txt) 정리 완료.", "gray")

            # 6. 로그 기록
            apply_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": new_version,
                "applied_files_count": applied_count,
            }
            self._log_apply(apply_log_path, apply_entry, log)

            summary = f"✅ 업데이트 버전 {new_version} 적용 완료. 총 {applied_count}개 파일 업데이트됨."
            log(summary, "lime")
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": "success", "summary": summary}
            
        except json.JSONDecodeError:
            error_message = f"❌ 업데이트 제안 파일({os.path.basename(proposal_path)}) 내용이 유효한 JSON 형식이 아닙니다."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 업데이트 적용 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    def _log_apply(self, log_path, entry, log):
        """업데이트 적용 로그를 기록합니다."""
        try:
            logs = []
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    try: 
                        logs = json.load(f)
                    except json.JSONDecodeError: 
                        logs = []
            
            logs.append(entry)

            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            log("  -> 업데이트 적용 내용이 로그 파일에 기록되었습니다.", "gray")
        except Exception as e:
            log(f"  -> ❌ 업데이트 로그 기록 실패: {e}", "red")

    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경
    def plugin_stop(self):
        self.logger("🛑 업데이트 적용 플러그인 종료됨", "gray")
        pass