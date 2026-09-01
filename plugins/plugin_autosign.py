from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_autosign.py
# 플러그인: 자동 승인 판단 (v1.2 - NoneType 오류 및 표준 구조 적용)

# -*- coding: utf-8 -*-
import sys
import io
import json
import os
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

class AutoSignPlugin(PCButlerPlugin):
    plugin_name = "자동 승인 판단"
    description = "진단 결과를 기반으로 자동 승인 여부를 판단하고 로그에 기록합니다."

    # --- 파일 이름 상수 정의 ---
    STATUS_FILE_NAME = "system_health_report.json"
    APPROVAL_FILE_NAME = "approval_ui.txt"
    LOG_FILE_NAME = "autosign_log.json"
    USER_CONFIG_FILE_NAME = "user_config.json"
    # --------------------------

    def read_status_file(self, path):
        """다양한 인코딩을 시도하여 status 파일을 안전하게 읽어옵니다."""
        encodings = ["utf-8", "cp949", "euc-kr"]
        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    return json.load(f)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return None # 실패 시 None 반환

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🤖 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)
        
        # 🚨 [구조 개선] 전체 로직을 하나의 try 블록으로 감싸 최종적인 반환을 보장
        try:
            # BASE_DIR을 settings에서 가져와 경로를 구성합니다.
            base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            reports_dir = os.path.join(base_path, "reports")
            config_dir = os.path.join(base_path, "config")
            
            # user_config.json 경로 설정 (자동 승인 규칙은 여기에 저장되어 있다고 가정)
            config_path = os.path.join(config_dir, self.USER_CONFIG_FILE_NAME)
            
            # 1. 설정 로드
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                summary = "⚠️ 사용자 설정 파일(user_config.json)을 로드할 수 없어 자동 승인을 건너뜜. (설정 파일 없음 또는 형식 오류)"
                log(summary, "yellow")
                self.progress(100)
                # 🚨 [필수] Warning 반환
                return {"status": "warning", "summary": summary}

            auto_approval_enabled = config.get("auto_approval_enabled", False)
            auto_approval_rules = config.get("auto_approval_rules", {})
            scan_target_path = config.get("scan_target_path") # 진단 결과 파일이 있는 상위 경로

            if not auto_approval_enabled:
                summary = "ℹ️ 자동 승인 기능이 설정 파일에서 비활성화되어 있습니다."
                log(summary, "white")
                self.progress(100)
                # 🚨 [필수] Info 반환
                return {"status": "info", "summary": summary}
            
            if not scan_target_path:
                 summary = "⚠️ scan_target_path 설정이 누락되어 자동 승인 판단을 건너뜜."
                 log(summary, "yellow")
                 self.progress(100)
                 # 🚨 [필수] Warning 반환
                 return {"status": "warning", "summary": summary}

            self.progress(30)
            
            # 2. 진단 결과 파일 찾기 및 로드
            status_path = os.path.join(reports_dir, self.STATUS_FILE_NAME)
            
            status_data = self.read_status_file(status_path)

            if status_data is None:
                summary = f"❌ 진단 결과 파일({self.STATUS_FILE_NAME}) 로드 실패. 자동 승인 불가. (파일 부재 또는 인코딩/JSON 형식 오류)"
                log(summary, "red")
                self.progress(100)
                # 🚨 [필수] Error 반환
                return {"status": "error", "summary": summary}

            system_name = status_data.get("system_name", "UNKNOWN_SYSTEM")
            system_status = status_data.get("status", "미확인").upper()
            
            log(f"🔍 시스템 진단 결과 확인: {system_name}, 상태: {system_status}", "white")
            self.progress(50)

            # 3. 자동 승인 규칙 판단
            is_approved = False
            reason = ""
            
            # 규칙 1: 신뢰할 수 있는 시스템 목록에 포함되어 있는가?
            trusted_systems = [s.upper() for s in auto_approval_rules.get("trusted_systems", [])]
            is_trusted = system_name.upper() in trusted_systems
            
            # 규칙 2: 승인 가능한 상태 목록에 포함되어 있는가?
            approved_statuses = [s.upper() for s in auto_approval_rules.get("status", [])]
            is_approved_status = system_status in approved_statuses

            if is_trusted and is_approved_status:
                is_approved = True
                reason = f"시스템({system_name})이 신뢰 목록에 있으며, 상태({system_status})가 승인 기준을 충족함."
            elif not is_trusted:
                reason = f"시스템({system_name})이 신뢰 목록에 포함되어 있지 않음. (현재 상태: {system_status})"
            elif not is_approved_status:
                reason = f"시스템은 신뢰 목록에 있으나, 현재 상태({system_status})가 승인 기준을 충족하지 않음."
            else:
                reason = "규칙 판단 실패." 

            self.progress(70)

            # 4. 결과 처리 및 파일 저장
            approval_path = os.path.join(reports_dir, self.APPROVAL_FILE_NAME)
            
            if is_approved:
                # 승인 파일 생성
                with open(approval_path, "w", encoding="utf-8") as f:
                    f.write("APPROVED")
                
                # 로그 기록
                self._log_sign(reports_dir, system_name, system_status, True, reason, log)
                
                summary = f"✅ 자동 승인 완료. '{system_name}'의 업데이트가 자동으로 적용됩니다. ({reason})"
                log(summary, "lime")
                final_status = "success"
            else:
                # 승인 파일이 남아있지 않도록 삭제
                if os.path.exists(approval_path):
                    os.remove(approval_path)
                
                # 로그 기록
                self._log_sign(reports_dir, system_name, system_status, False, reason, log)
                
                summary = f"⚠️ 자동 승인 불가. '{system_name}'은 수동 승인이 필요합니다. ({reason})"
                log(summary, "yellow")
                final_status = "warning"
                
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": summary}
            
        except Exception as e:
            error_message = f"❌ 자동 승인 판단 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}

    def _log_sign(self, reports_dir, system, status, approved, reason, log):
        """자동 승인 로그를 기록합니다."""
        log_path = os.path.join(reports_dir, self.LOG_FILE_NAME)
        try:
            logs = []
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    try: 
                        logs = json.load(f)
                    except json.JSONDecodeError: 
                        logs = []
            
            logs.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system": system,
                "status": status,
                "approved": approved,
                "reason": reason
            })

            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            log("  -> 자동 승인 판단 내용이 로그 파일에 기록되었습니다.", "gray")
        except Exception as e:
            log(f"  -> ❌ 자동 승인 로그 기록 실패: {e}", "red")

    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경
    def plugin_stop(self):
        self.logger("🛑 자동 승인 플러그인 종료됨", "gray")
        pass