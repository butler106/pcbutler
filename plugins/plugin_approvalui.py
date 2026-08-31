from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_approvalui.py
# 플러그인: 관리자 승인 UI (미완성 처리 버전)

# -*- coding: utf-8 -*-
import sys
import io

# 스크립트의 표준 출력(stdout)과 표준 오류(stderr)의 인코딩을 UTF-8로 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')

import json
import os

class ApprovalUIPlugin(PCButlerPlugin):
    plugin_name = "관리자 승인 UI"
    description = "자동 승인 결과를 기반으로 승인/보류 시스템을 시각적으로 정리합니다."

    # 🚨 [필수 추가] def run(...) 메서드를 추가하고 WARNING을 반환하여 오류를 방지합니다.
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        self.logger(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (미완성/GUI 전용)", "cyan")
        
        # UI 관련 플러그인은 콘솔 환경에서 실행되지 않으므로 WARNING을 반환하여 건너뜁니다.
        summary = "플러그인 기능이 미완성되었거나 콘솔 환경에서 지원되지 않습니다."
        self.logger(f"⚠️ [경고] {self.plugin_name} : {summary}", "yellow")
        self.progress(100)
        return {"status": "WARNING", "summary": summary}
        
    def execute_plugin(self, base_path="E:/PCButler_v106"):
        # run() 메서드가 실행되는 환경에서는 이 로직은 무시됩니다.
        print("🧩 관리자 승인 UI 생성 중...")

        approval_path = os.path.join(base_path, "reports", "approval_log.json")
        ui_path = os.path.join(base_path, "reports", "approval_ui.txt")

        if not os.path.exists(approval_path):
            print(f"❌ 승인 로그 없음: {approval_path}")
            return

        try:
            with open(approval_path, "r", encoding="utf-8-sig") as f:
                approvals = json.load(f)

            approved = []
            pending = []

            for entry in approvals:
                sys_id = entry.get("system_id")
                decision = entry.get("decision")
                timestamp = entry.get("timestamp")

                line = f"{sys_id} | {decision} | {timestamp}"
                if decision == "자동 승인":
                    approved.append(line)
                else:
                    pending.append(line)

            lines = []
            lines.append("[✅ 자동 승인 시스템]")
            lines.extend(approved if approved else ["(없음)"])
            lines.append("")
            lines.append("[⏳ 보류 시스템]")
            lines.extend(pending if pending else ["(없음)"])
            lines.append("")

            with open(ui_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"✅ [완료] 승인 UI 보고서 생성 → {ui_path}")

        except Exception as e:
            print(f"⚠️ 승인 UI 생성 실패: {e}")

            # 🚨 [자동 삽입] 결과 반환 누락 오류 방지 (자동화 스크립트)
            summary = "플러그인 기능이 미완성되었거나 콘솔 환경에서 지원되지 않습니다."
            return {"status": "WARNING", "summary": summary}
        
    def plugin_stop(self):
        print("🚩 승인 UI 플러그인 종료됨")
        # 🚨 잘못된 위치에 있던 return 코드를 제거했습니다.

if __name__ == "__main__":
    print("🔌 플러그인 단독 실행 테스트 시작...")
    plugin = ApprovalUIPlugin()
    plugin.execute_plugin()
    plugin.plugin_stop()