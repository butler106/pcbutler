from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import psutil
import time 

class DiskCheckPlugin(PCButlerPlugin):
    """
    시스템의 디스크 사용량을 확인하고, 사용률이 높은 디스크에 경고를 표시합니다.
    """
    plugin_name = "Diskcheck"
    description = "디스크 사용량 및 상태를 점검합니다."
    version = "1.2.0" # 상태 경고 로직 포함

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        
    # 타입 힌트를 포함한 표준 run 메서드 정의
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (디스크 상태 점검)", "cyan")
        self.progress(1)

        try:
            # 🚨 [CRITICAL FIX]: 중단 확인 로직 통일
            if stop_check and stop_check():
                log("  -> ⚠️ 디스크 점검 중단 요청 수신.", "yellow")
                return {"status": "warning", "summary": "⚠️ 사용자 요청으로 디스크 점검 중단됨."}

            disk_partitions = psutil.disk_partitions(all=False)
            disks_info = []
            high_usage_disks_count = 0
            
            for i, partition in enumerate(disk_partitions):
                self.progress(5 + int(90 * (i + 1) / len(disk_partitions)))
                
                # 🚨 [CRITICAL FIX]: 반복문 내 중단 확인
                if stop_check and stop_check():
                    log("  -> ⚠️ 디스크 점검 중단 요청 수신.", "yellow")
                    return {"status": "warning", "summary": "⚠️ 사용자 요청으로 디스크 점검 중단됨."}
                    
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    usage_percent = usage.percent
                    total_gb = usage.total / (1024**3)
                    used_gb = usage.used / (1024**3)
                    free_gb = usage.free / (1024**3)
                    
                    status = "success"
                    # 🚨 [CRITICAL FIX]: 사용률에 따른 상태 변경 로직
                    if usage_percent >= 90:
                        status = "error" # 90% 이상은 위험
                        high_usage_disks_count += 1
                    elif usage_percent >= 70:
                        status = "warning" # 70% 이상은 경고
                        
                    disks_info.append({
                        "mountpoint": partition.mountpoint,
                        "device": partition.device,
                        "fstype": partition.fstype,
                        "status": status,
                        "usage_percent": round(usage_percent, 1),
                        "total_gb": round(total_gb, 2),
                        "used_gb": round(used_gb, 2),
                        "free_gb": round(free_gb, 2)
                    })
                except Exception as e:
                    log(f"  -> ❌ 디스크 ({partition.mountpoint}) 정보 수집 실패: {e}", "yellow")
                    
            # 최종 요약 (전체 플러그인의 상태를 결정)
            total_count = len(disks_info)
            status = "success"
            summary = f"총 {total_count}개 디스크 상태 양호. 사용량이 높은 디스크 없음."
            
            if high_usage_disks_count > 0:
                summary = f"🚨 경고: 총 {total_count}개 디스크 중 {high_usage_disks_count}개의 디스크 사용량이 90% 이상입니다."
                status = "error"
            elif any(d['status'] == 'warning' for d in disks_info):
                summary = f"⚠️ 경고: 일부 디스크 사용량이 70%를 초과합니다. 공간 확보를 고려하십시오."
                status = "warning"
            
            log(summary, "lime" if status == "success" else "red" if status == "error" else "yellow")

            details = {"disks": disks_info}
            final_result = {"status": status, "summary": summary, "details": details}
            self.progress(100)
            
            # 🚨 [CRITICAL FIX]: JSON 결과 파일 저장
            self._save_result_to_file(final_result) 
            
            return final_result

        except Exception as e:
            error_message = f"❌ 디스크 점검 중 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": error_message}
