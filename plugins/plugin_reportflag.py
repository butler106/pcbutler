from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 중요 보고서 지정 (ReportFlag) - 최종 완벽 버전
# - 콘솔 환경에서 보고서를 중요 항목으로 지정하여 자동 삭제 대상에서 제외합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import sys
import re

class ReportFlagPlugin(PCButlerPlugin):
    """
    사용자가 보고서를 중요 항목으로 지정하여 자동 삭제 대상에서 제외할 수 있도록 합니다.
    지정된 파일 목록은 'reports/keep_list.txt'에 저장됩니다.
    """
    plugin_name = "중요 보고서 지정"
    description = "사용자가 보고서를 중요 항목으로 지정하여 자동 삭제 대상에서 제외할 수 있도록 합니다."
    version = "2.1.0" # 경로 안정화 및 입력 로직 보강

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # BASE_DIR을 settings에서 가져와 reports 경로를 구성 (표준 구조)
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.report_dir = os.path.join(base_path, 'reports')
        self.flag_file = os.path.join(self.report_dir, "keep_list.txt")

    def _parse_input(self, user_input, max_index):
        """사용자 입력을 분석하여 선택된 인덱스 리스트를 반환합니다."""
        selected_indices = set()
        
        if user_input.lower() in ('a', 'all'):
            # 'all' 선택 시 모든 파일 선택
            return list(range(max_index)) 

        # 쉼표(,)로 구분된 항목들을 처리
        for item in user_input.split(','):
            item_strip = item.strip()
            if not item_strip:
                continue

            # 범위 입력 처리 (예: 1-3)
            if '-' in item_strip:
                try:
                    start, end = map(int, item_strip.split('-'))
                    # 1부터 시작하는 인덱스를 0부터 시작하는 리스트 인덱스로 변환
                    for i in range(max(1, start), min(max_index, end) + 1):
                        selected_indices.add(i - 1)
                except ValueError:
                    self.logger(f"⚠️ 경고: 잘못된 범위 형식 '{item_strip}'는 무시됩니다.", "yellow")
            
            # 단일 숫자 입력 처리 (예: 5)
            else:
                try:
                    index = int(item_strip)
                    if 1 <= index <= max_index:
                        selected_indices.add(index - 1)
                    else:
                        self.logger(f"⚠️ 경고: 유효하지 않은 번호 '{index}'는 무시됩니다. (1 ~ {max_index} 사이)", "yellow")
                except ValueError:
                    self.logger(f"⚠️ 경고: 잘못된 번호 형식 '{item_strip}'는 무시됩니다.", "yellow")
                    
        return sorted(list(selected_indices))

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)
        
        final_status = "success"
        
        log(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")
        
        try:
            # reports 디렉토리가 없으면 생성 (안전장치)
            if not os.path.exists(self.report_dir):
                os.makedirs(self.report_dir, exist_ok=True) 
                log(f"  -> ℹ️ 보고서 디렉토리 생성: {self.report_dir}", "white")

            # .zip, .txt, keep_list.txt 파일을 제외한 보고서 파일 목록 (.html, .pdf 등)
            files = [
                f for f in os.listdir(self.report_dir) 
                if os.path.isfile(os.path.join(self.report_dir, f)) 
                and not f.endswith(('.zip', '.txt', '.json', 'keep_list.txt'))
            ]
            
            # 최신 파일부터 먼저 표시하기 위해 수정 시간을 기준으로 정렬
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.report_dir, x)), reverse=True)
            
            self.progress(20)

            if not files:
                final_summary = "ℹ️ reports 폴더에서 플래그를 지정할 보고서 파일을 찾을 수 없습니다."
                log(final_summary, "white")
                self.progress(100)
                return {"status": "success", "summary": final_summary}

            # 1. 보고서 목록 출력
            log("\n--- [보고서 목록] ---", "yellow")
            for i, fname in enumerate(files):
                fpath = os.path.join(self.report_dir, fname)
                mtime = os.path.getmtime(fpath)
                mdate = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                log(f"  [{i + 1}] {fname} (생성일: {mdate})", "white")
            log("-------------------\n", "yellow")
            
            # 2. 사용자 입력 대기 (비대화형 환경 확인)
            if not sys.stdin.isatty():
                final_summary = "ℹ️ 콘솔이 비대화형 모드입니다. 중요 보고서 지정을 건너뜁니다."
                log(final_summary, "white")
                self.progress(100)
                return {"status": "success", "summary": final_summary}
                
            prompt = "📌 중요 보고서로 지정할 번호를 쉼표(,)나 범위(-)로 입력하세요. (예: 1,3,5 또는 1-3). 취소하려면 Enter: "
            user_input = input(prompt)
            
            if not user_input.strip():
                final_summary = "ℹ️ 사용자 입력이 없어 중요 보고서 지정을 취소합니다."
                log(final_summary, "white")
                self.progress(100)
                return {"status": "success", "summary": final_summary}
            
            self.progress(50)

            # 3. 입력 분석
            selected_indices = self._parse_input(user_input, len(files))
            
            if not selected_indices:
                final_summary = "ℹ️ 유효하게 선택된 보고서가 없어 아무 작업도 수행하지 않습니다."
                log(final_summary, "white")
                self.progress(100)
                return {"status": "success", "summary": final_summary}

            selected_files = [files[i] for i in selected_indices]
            
            # 4. keep_list.txt에 기록 (덮어쓰기)
            with open(self.flag_file, "w", encoding="utf-8") as f:
                for fname in selected_files:
                    f.write(fname + "\n")
            
            log(f"✅ 중요 보고서로 지정 완료: {os.path.basename(self.flag_file)}", "lime")
            log(f"   -> 지정된 파일: {', '.join(selected_files)}", "lime")
            final_summary = f"총 {len(selected_files)}개의 보고서가 중요 항목으로 지정되었습니다."
            
            self.progress(100)

            # 🚨 최종 결과 반환
            return {"status": final_status, "summary": final_summary}
            
        except Exception as e:
            error_message = f"❌ 중요 보고서 지정 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}

# 추가된 의존성 임포트 (datetime)
from datetime import datetime