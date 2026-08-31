from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_autoapprove.py
# 자동 승인 규칙 기반 처리 플러그인 (v1.1 - 비-JSON 파일 건너뛰기 기능 추가)

# -*- coding: utf-8 -*-
import sys
import io

# 스크립트의 표준 출력(stdout)과 표준 오류(stderr)의 인코딩을 UTF-8로 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')

# --- 아래에 기존 플러그인 코드를 그대로 두시면 됩니다 ---

import os
import json
import shutil
from datetime import datetime

class AutoApprovePlugin(PCButlerPlugin):
    plugin_name = "규칙 기반 자동 승인"
    description = "지정된 경로의 파일들을 규칙에 따라 자동으로 승인/분류합니다."

    RULES_CONFIG = "approval_rules.json"

    # 🚨 [핵심 수정] run 메서드: execute_plugin 대신 메인 로직을 통합하고 결과 반환
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        self.logger(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)
        
        status = "SUCCESS"
        approved_count = 0
        
        try:
            # 1. 로직 실행을 위한 기본 경로 및 설정 로드
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_path, "config", self.RULES_CONFIG)
            
            if not os.path.exists(config_path):
                self.logger(f"🚫 자동 승인 규칙 파일({self.RULES_CONFIG})이 없습니다.", "yellow")
                self.progress(100)
                return {"status": "WARNING", "summary": "규칙 파일 없음"}

            with open(config_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            
            # 폴더 설정
            reports_dir = os.path.join(base_path, "reports")
            approved_dir = os.path.join(reports_dir, "approved")
            review_dir = os.path.join(reports_dir, "review_required")
            os.makedirs(approved_dir, exist_ok=True)
            os.makedirs(review_dir, exist_ok=True)
            
            # 규칙 로드
            trusted_systems = set(rules.get("trusted_systems", []))
            approved_statuses = set(rules.get("approved_statuses", []))
            
            self.progress(30)
            
            # 2. reports 폴더 내 파일 처리
            files_to_check = [f for f in os.listdir(reports_dir) if os.path.isfile(os.path.join(reports_dir, f)) and f.endswith(".json")]
            total_files = len(files_to_check)
            self.logger(f"📝 총 {total_files}개의 보고서 파일 점검 시작.", "white")

            for i, filename in enumerate(files_to_check):
                file_path = os.path.join(reports_dir, filename)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        report = json.load(f)
                    
                    system = report.get("system_name", "Unknown")
                    status_text = report.get("status", "Unknown")
                    
                    if system in trusted_systems and status_text in approved_statuses:
                        self.logger(f"  -> ✅ 자동 승인: {filename} (System: {system}, Status: {status_text})", "lime")
                        shutil.move(file_path, os.path.join(approved_dir, filename))
                        approved_count += 1
                    else:
                        self.logger(f"  -> ❌ 수동 확인 필요: {filename} (System: {system}, Status: {status_text})", "yellow")
                        shutil.move(file_path, os.path.join(review_dir, filename))

                except json.JSONDecodeError:
                    self.logger(f"  -> ℹ️ JSON 형식 오류. 수동 확인 폴더로 이동: {filename}", "gray")
                    shutil.move(file_path, os.path.join(review_dir, filename))
                except Exception as e:
                    self.logger(f"  -> ⚠️ 파일 처리 오류 ({filename}): {e}", "red")
                    status = "ERROR" # 처리 중 오류 발생 시 ERROR 상태 설정
                    
                self.progress(30 + int((i + 1) / total_files * 60)) # 진행률 업데이트
                
            summary = f"👍 자동 승인 작업 완료. 총 {approved_count}개 파일 자동 승인 처리됨."
            
        except Exception as e:
            self.logger(f"❌ 자동 승인 실행 중 치명적 오류 발생: {e}", "red")
            status = "ERROR"
            summary = f"치명적 오류 발생: {e}"
            
        self.progress(100)
        
        # 3. 최종 결과 반환
        return {"status": status, "summary": summary}
        
    # 🚨 기존 execute_plugin()은 삭제하거나 비워두어 run()으로 기능을 통일합니다.
    def execute_plugin(self, data=None):
        return