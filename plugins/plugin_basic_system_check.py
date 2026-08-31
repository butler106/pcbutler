from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 기본 시스템 점검 (BasicSystemCheck) - 최종 통합 버전
# - run() 메서드에 최종 결과 반환 로직 및 디스크 정보 추가
# ==============================================================================
from plugin_base import PCButlerPlugin
import platform
import psutil
import os
import sys

# Windows에서 바이트를 기가바이트(GB)로 변환하는 헬퍼 함수
def bytes_to_gb(bytes_val):
    """바이트 값을 기가바이트로 변환합니다."""
    return bytes_val / (1024 ** 3)

class BasicSystemCheckPlugin(PCButlerPlugin):
    """
    운영체제, CPU, 메모리 등 기본적인 시스템 정보를 점검합니다.
    """
    plugin_name = "기본 시스템 정보 점검"
    description = "운영체제, CPU, 메모리, 디스크 등 기본적인 시스템 정보를 점검합니다."
    version = "2.0.0"
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    # 🚨 [핵심 수정] run 메서드 구현
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)
        
        final_status = "success"
        final_summary = "기본 시스템 정보 점검 완료."
        system_data = {}

        try:
            log(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
            
            # 1. OS 및 CPU 정보
            system_data['os'] = platform.platform()
            system_data['cpu'] = platform.processor()
            log(f"  -> 🖥️ 운영체제: {system_data['os']}", "lime")
            log(f"  -> 💡 프로세서: {system_data['cpu']}", "lime")
            self.progress(30)
            
            # 2. 메모리(RAM) 정보
            mem_info = psutil.virtual_memory()
            total_ram_gb = bytes_to_gb(mem_info.total)
            used_ram_gb = bytes_to_gb(mem_info.used)
            ram_percent = mem_info.percent
            
            system_data['ram'] = {
                "total_gb": f"{total_ram_gb:.2f} GB",
                "used_gb": f"{used_ram_gb:.2f} GB",
                "percent": ram_percent
            }
            
            log(f"  -> 💾 총 메모리(RAM): {system_data['ram']['total_gb']}", "lime")
            log(f"  -> 📈 메모리 사용률: {ram_percent:.1f}%", "lime")
            self.progress(60)

            # 3. 디스크 정보 (C: 드라이브 점검 및 상태 판단 로직 추가)
            disk_data = []
            if sys.platform.startswith('win'): 
                try:
                    disk_usage = psutil.disk_usage('C:\\')
                    total_disk_gb = bytes_to_gb(disk_usage.total)
                    used_disk_gb = bytes_to_gb(disk_usage.used)
                    disk_percent = disk_usage.percent

                    disk_data.append({
                        "drive": "C:",
                        "total_gb": f"{total_disk_gb:.2f} GB",
                        "used_gb": f"{used_disk_gb:.2f} GB",
                        "percent": disk_percent
                    })

                    log(f"  -> 💽 C: 드라이브 총 용량: {disk_data[0]['total_gb']}", "lime")
                    log(f"  -> 📊 C: 드라이브 사용률: {disk_percent:.1f}%", "lime")
                    
                    if disk_percent > 90.0:
                        final_status = "error"
                        final_summary = f"C: 드라이브 용량이 {disk_percent:.1f}%로 매우 부족합니다."
                        log("❌ [오류] C: 드라이브 용량 부족! 불필요한 파일 정리가 필요합니다.", "red")
                    elif disk_percent > 80.0:
                        if final_status != "error":
                            final_status = "warning"
                            final_summary = f"C: 드라이브 용량이 {disk_percent:.1f}%로 여유가 부족합니다."
                            log("⚠️ [경고] C: 드라이브 용량이 부족합니다. 정리를 권장합니다.", "yellow")

                except FileNotFoundError:
                    log("⚠️ [경고] C: 드라이브 정보 접근 불가.", "yellow")
                except Exception as e:
                    log(f"❌ [오류] 디스크 정보 조회 실패: {e}", "red")

            system_data['disk'] = disk_data
            self.progress(90)
            
            log(f"\n✅ '{self.plugin_name}' 작업을 완료했습니다. 상태: {final_status.upper()}", "lime")

            self.progress(100)
            
            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": final_summary, "data": system_data}

        except Exception as e:
            error_message = f"❌ 기본 시스템 점검 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}
            
    # 🚨 [추가] 표준 형식에 맞춘 plugin_stop 메서드
    def plugin_stop(self):
        self.logger("🛑 기본 시스템 점검 플러그인 종료됨", "gray")
        pass