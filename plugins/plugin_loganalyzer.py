from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_loganalyzer.py
# 플러그인: 진단 로그 분석 (v2.0 - 표준 구조 및 Logger 적용)
import os
import re
from datetime import datetime

class LogAnalyzerPlugin(PCButlerPlugin):
    plugin_name = "진단 로그 분석"
    description = "플러그인 실행 로그를 분석하여 오류, 경고, 실행 시간 등을 요약합니다."
    version = "2.0.0"

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)
        
        final_status = "success"
        final_summary = "로그 분석 및 요약 완료."
        
        try:
            log("📈 진단 로그 분석 시작...", "cyan")
            # [수정] reports 폴더는 BASE_DIR을 기준으로 설정되므로, 여기서는 상대 경로만 사용
            log_path = os.path.join("reports", "butler_log.txt")
            summary_path = os.path.join("reports", "log_summary.txt")

            # BASE_DIR을 기준으로 log_path의 실제 경로를 구성 (PCButlerPlugin에서 제공하는 base_path가 있다면 사용)
            if hasattr(self, 'base_path'):
                full_log_path = os.path.join(self.base_path, log_path)
            else:
                full_log_path = log_path

            if not os.path.exists(full_log_path):
                final_summary = "⚠️ 로그 파일(butler_log.txt)이 존재하지 않아 분석을 건너뜁니다."
                log(final_summary, "yellow")
                self.progress(100)
                # 🚨 [필수] 최종 결과 반환
                return {"status": "warning", "summary": final_summary}
            
            self.progress(30)

            errors = []
            warnings = []
            executions = []
            
            # 로그 파일 읽기
            with open(full_log_path, "r", encoding="utf-8", errors='ignore') as f:
                for line in f:
                    if "실행 시작" in line and "플러그인" in line:
                        # 실행 시작 라인
                        executions.append(line.strip())
                    elif "⚠️" in line:
                        # 경고 라인 (⚠️)
                        warnings.append(line.strip())
                    elif "❌" in line or "오류" in line or "실패" in line:
                        # 오류 라인 (❌, 오류, 실패)
                        errors.append(line.strip())
            
            self.progress(70)

            # 요약 파일 작성
            full_summary_path = summary_path
            if hasattr(self, 'base_path'):
                full_summary_path = os.path.join(self.base_path, summary_path)
                
            os.makedirs(os.path.dirname(full_summary_path), exist_ok=True)
            
            with open(full_summary_path, "w", encoding="utf-8") as f:
                f.write("📋 Butler 진단 로그 요약\n")
                f.write(f"⏱️ 분석 시점: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                f.write(f"📊 실행된 플러그인 수: {len(executions)}개\n")
                f.write(f"⚠️ 경고 발생 수: {len(warnings)}건\n")
                f.write(f"❌ 오류 발생 수: {len(errors)}건\n\n")

                if errors:
                    f.write("🚨 주요 ❌ 오류 목록:\n")
                    for e in errors:
                        f.write(f" - {e}\n")
                    f.write("\n")

                if warnings:
                    f.write("⚠️ 주요 ⚠️ 경고 목록:\n")
                    for w in warnings:
                        f.write(f" - {w}\n")
                    f.write("\n")
                
                f.write("⭐ 실행된 플러그인 목록 (시작 시점 기준):\n")
                for e in executions:
                    f.write(f" - {e}\n")
                f.write("\n")
            
            log(f"✅ 로그 분석 완료 및 요약 보고서 생성 → {summary_path}", "lime")
            final_summary = f"총 {len(errors)}건의 오류와 {len(warnings)}건의 경고가 요약 보고서에 기록되었습니다."
            
            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": final_summary}
            
        except Exception as e:
            error_message = f"❌ 로그 분석 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}
            
    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경
    def plugin_stop(self):
        self.logger("🛑 진단 로그 분석 플러그인 종료됨", "gray")
        pass