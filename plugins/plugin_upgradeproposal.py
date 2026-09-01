from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_upgradeproposal.py
# Butler 개선 제안 플러그인 (v2.2 – NoneType 오류 및 표준 구조 적용, 예외 처리 구조 수정)

# -*- coding: utf-8 -*-
import sys
import io
import os
import json
from datetime import datetime

# 콘솔 인코딩 문제 방지
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

class UpgradeProposalPlugin(PCButlerPlugin):
    plugin_name = "업데이트 제안 생성"
    description = "규칙 파일을 기반으로 시스템 상태를 분석하여 개선 작업을 자동으로 제안합니다."

    # --- 파일 이름 상수 정의 ---
    STATUS_FILE = "system_health_report.json" 
    PROPOSAL_FILE = "update_proposal.json"
    RULES_FILE = "proposal_rules.json"
    # --------------------------

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🧠 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)
        
        # 1. 경로 설정 (config 디렉토리)
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_dir = os.path.join(base_path, "config")
        
        # 파일 경로 설정
        status_path = os.path.join(config_dir, self.STATUS_FILE)
        proposal_path = os.path.join(config_dir, self.PROPOSAL_FILE)
        rules_path = os.path.join(config_dir, self.RULES_FILE)
        
        # 🚨 [수정]: 전체 로직을 하나의 try 블록으로 감싸서 마지막의 Syntax Error를 해결하고 모든 오류를 처리
        try:
            # 2-1. 상태 파일 로드
            try:
                with open(status_path, "r", encoding='utf-8') as f:
                    status_data = json.load(f)
                log(f"  -> ✅ 시스템 상태 파일 로드 완료: {self.STATUS_FILE}", "gray")
            except FileNotFoundError:
                error_message = f"❌ 시스템 상태 파일({self.STATUS_FILE})을 찾을 수 없습니다. (먼저 SystemCheck를 실행하세요)"
                log(error_message, "red")
                self.progress(100)
                return {"status": "error", "summary": error_message}

            # 2-2. 규칙 파일 로드
            try:
                with open(rules_path, "r", encoding='utf-8') as f:
                    rules = json.load(f)
                log(f"  -> ✅ 제안 규칙 파일 로드 완료: {self.RULES_FILE}", "gray")
            except FileNotFoundError:
                error_message = f"❌ 제안 규칙 파일({self.RULES_FILE})을 찾을 수 없습니다. (config 디렉토리를 확인하세요)"
                log(error_message, "red")
                self.progress(100)
                return {"status": "error", "summary": error_message}

            self.progress(30)
            
            # 3. 규칙 기반 분석
            matched_rule = "None"
            proposal_action = {}
            # 상태 데이터가 유효하지 않을 경우를 대비하여 기본값 "UNKNOWN" 설정
            current_status = status_data.get("overall_status", "UNKNOWN").upper() 
            
            # 🚨 [핵심 로직]: 실제 규칙 매칭 및 제안 생성 로직
            for rule_name, action in rules.items():
                # rule_name이 상태와 일치하는지 확인하는 간소화된 로직
                if current_status in rule_name.upper():
                    matched_rule = rule_name
                    proposal_action = action
                    break
            
            if matched_rule != "None":
                log(f"  -> 🔍 규칙 매칭 성공: '{matched_rule}'에 따라 개선 작업 제안을 생성합니다.", "yellow")
            else:
                summary = f"✅ 일치하는 개선 제안 규칙이 없습니다. (상태: {current_status})"
                log("  -> ✅ 일치하는 개선 규칙이 없습니다. (양호 또는 규칙 미정의)", "lime")
                self.progress(100)
                # 🚨 [필수] 매칭되는 규칙이 없으면 성공으로 반환
                return {"status": "success", "summary": summary}

            self.progress(70)

            # 4. 제안 JSON 데이터 구성
            proposal = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rule_id": matched_rule,
                "system": status_data.get("system_name", "UNKNOWN"),
                "status": current_status,
                "recommendation": proposal_action.get("recommendation", ""),
                "files": proposal_action.get("proposal_files", []) 
            }

            # 5. 제안 JSON 파일 저장
            os.makedirs(config_dir, exist_ok=True)
            with open(proposal_path, "w", encoding="utf-8") as f:
                json.dump(proposal, f, ensure_ascii=False, indent=2)
            
            summary = f"✅ 개선 제안 생성 완료: {os.path.basename(proposal_path)} (규칙: {matched_rule})"
            log(summary, "lime")
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": "success", "summary": summary}
            
        # 6. 최상위 예외 처리 (JSONDecodeError 및 일반 오류)
        except json.JSONDecodeError as e:
            # 상태 파일이나 규칙 파일 로드 중 JSON 형식 오류 발생 시 처리
            error_message = f"❌ 상태/규칙 파일 형식이 유효하지 않음 (JSONDecodeError): {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            # 기타 예상치 못한 오류 발생 시 처리
            error_message = f"❌ 개선 제안 생성 중 예상치 못한 오류 발생: {type(e).__name__} - {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}