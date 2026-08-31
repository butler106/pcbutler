from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 보고서 정리 (ReportCleanup) - 최종 완벽 버전
# - 오래된 진단 보고서 파일을 정리합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import os
import shutil
from datetime import datetime, timedelta
import time # 시뮬레이션 용

class ReportCleanupPlugin(PCButlerPlugin):
    """
    오래된 진단 보고서 파일을 정리합니다.
    (기본 설정: 30일 초과 파일 삭제)
    """
    plugin_name = "보고서 정리"
    description = "오래된 진단 보고서 파일(기본 30일 초과)을 삭제하여 저장 공간을 확보합니다."
    version = "2.0.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description
        
        # reports 폴더 경로 (BASE_DIR을 기준으로 설정)
        # plugins 폴더의 상위 폴더에 reports가 있다고 가정
        self.base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.report_dir = os.path.join(self.base_path, 'reports') 

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        # 1. 설정 값 확인 및 유효성 검사
        # 기본값 30일, 0 이하면 비활성화
        cleanup_days = self.settings.get("report_cleanup_days", 30)
        
        if cleanup_days <= 0:
            summary = "보고서 정리 기능이 비활성화되었습니다 (cleanup_days = 0)."
            log(f"  -> ℹ️ {summary}", "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
        
        # 2. 정리 기준 날짜 계산
        cutoff_date = datetime.now() - timedelta(days=cleanup_days)
        
        log(f"  -> 📅 정리 기준: {cleanup_days}일 초과 (기준일: {cutoff_date.strftime('%Y-%m-%d')})", "white")
        self.progress(10)
        
        deleted_count = 0
        total_size = 0 # 바이트 단위
        
        try:
            # reports 폴더가 없으면 생성 (생성되어도 정리할 파일이 없으므로 무시)
            if not os.path.exists(self.report_dir):
                summary = f"ℹ️ 보고서 디렉토리({self.report_dir})가 존재하지 않아 정리 작업을 건너뜁니다."
                log(summary, "white")
                self.progress(100)
                return {"status": "success", "summary": summary}

            # 3. reports 폴더 순회 및 정리
            all_items = os.listdir(self.report_dir)
            
            for i, item_name in enumerate(all_items):
                # 작업 중지 요청 확인
                # 🚨 FIX (2026-08-31): self.stop_event는 애초에 존재하지 않는 속성이었다
                # (plugin_base.py의 PCButlerPlugin은 stop_event를 정의하지 않으며,
                #  중지 여부는 run()에 전달되는 stop_check 콜백으로 확인해야 한다).
                # 오타(self.self.stop_event)까지 겹쳐 실행 시 항상
                # "'ReportCleanupPlugin' object has no attribute 'stop_event'" 오류로 죽었다.
                if stop_check and stop_check():
                    log("  -> 🛑 작업 중지 요청이 감지되었습니다.", "yellow")
                    break

                item_path = os.path.join(self.report_dir, item_name)

                # 현재 플러그인과 로그 파일은 정리 대상에서 제외 (실행 중인 파일이므로)
                if item_name in ['butler_log.txt', f"Analysis_Report_{self.analysis_id}.html", f"Analysis_Report_{self.analysis_id}.zip"]:
                    continue
                
                try:
                    # 파일/폴더의 마지막 수정 시간 (Time of last modification)을 확인
                    mtime_timestamp = os.path.getmtime(item_path)
                    item_date = datetime.fromtimestamp(mtime_timestamp)

                    # 기준일보다 오래된 경우 (작거나 같으면 삭제 대상)
                    if item_date <= cutoff_date:
                        log(f"  -> 🗑️ 삭제 대상: {item_name} (수정일: {item_date.strftime('%Y-%m-%d')})", "gray")
                        
                        if os.path.isfile(item_path):
                            total_size += os.path.getsize(item_path)
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                             # 폴더 삭제 (하위 파일 모두 포함)
                             # shutil.rmtree는 폴더와 내용을 모두 삭제합니다.
                             # 실제 삭제 전에 폴더 크기 계산은 복잡하므로, 일단 파일만 계산하고 폴더는 0으로 처리
                             shutil.rmtree(item_path)
                             
                        deleted_count += 1
                
                except FileNotFoundError:
                    # 이미 다른 프로세스에 의해 삭제되었을 경우
                    continue
                except PermissionError:
                    log(f"  -> ❌ 접근 권한 오류: {item_name}. 관리자 권한으로 실행해야 합니다.", "red")
                except Exception as file_error:
                    log(f"  -> ❌ 파일/폴더 처리 중 오류: {item_name}, {file_error}", "red")

                # 진행률 업데이트 (최소 90%까지)
                self.progress(10 + int(80 * (i + 1) / len(all_items)))

            self.progress(100)
            
            # 4. 최종 결과 요약
            if deleted_count > 0:
                # 바이트를 메가바이트로 변환
                deleted_size_mb = total_size / (1024**2)
                summary = f"✅ {deleted_count}개의 오래된 보고서 파일을 정리했습니다. (총 {deleted_size_mb:.2f} MB)"
                status = "success"
                log(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime")
            else:
                summary = "✅ 정리 대상인 오래된 보고서 파일이 없습니다."
                status = "success"
                log(f"\n✅ '{self.name}' 작업을 완료했습니다. ({summary})", "lime")
                
            return {"status": status, "summary": summary, "deleted_count": deleted_count}

        except Exception as e:
            error_message = f"❌ 보고서 정리 작업 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}