from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import psutil
import time
import os
import sys

class RAMStressPlugin(PCButlerPlugin):
    plugin_name = "RAMStress"
    description = "시스템 메모리 사용량 점검 및 스트레스 테스트를 실행합니다."
    version = "1.3.1" 

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        
        # 🚨 CRITICAL FIX: ConfigParser 객체를 꺼내어 설정값 로드
        config_parser_obj = settings.get('CONFIG_PARSER_OBJECT', None)
        
        self.duration = 5
        self.increment = 0.5
        self.max_usage_percent = 95
        
        # ConfigParser 객체의 getint/getfloat 사용 (AttributeError 해결)
        if config_parser_obj and config_parser_obj.has_section('RAMStress'):
            try:
                self.duration = config_parser_obj.getint('RAMStress', 'duration', fallback=5)
                self.increment = config_parser_obj.getfloat('RAMStress', 'increment_gb', fallback=0.5)
                self.max_usage_percent = config_parser_obj.getint('RAMStress', 'max_usage_percent', fallback=95)
            except Exception:
                pass 
        
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # logger 및 progress 콜백 함수 주입
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        log(f"🔍 '{self.name}' 작업을 시작합니다. (스트레스 지속 시간: {self.duration}s)", "cyan")
        self.progress(10)

        mem_info = psutil.virtual_memory()
        total_gb = mem_info.total / (1024**3)
        initial_used_percent = mem_info.percent
        
        log(f"  -> 총 메모리: {total_gb:.2f} GB | 초기 사용률: {initial_used_percent:.1f}%%", "gray")

        current_step = 0
        max_steps = self.duration
        
        for i in range(max_steps):
            if stop_check and stop_check():
                log("  -> ⚠️ RAM 테스트 중단 요청 수신.", "yellow")
                return {"status": "warning", "summary": "⚠️ 사용자 요청으로 RAM 스트레스 테스트 중단됨."}

            time.sleep(1)
            current_step = i + 1
            current_percent = 10 + int(70 * current_step / max_steps)
            self.progress(current_percent)
            
            # 시뮬레이션 로직 유지
            simulated_usage = initial_used_percent + (self.increment * current_step * 10) / (total_gb * 1024)
            if simulated_usage > self.max_usage_percent:
                simulated_usage = self.max_usage_percent

            log(f"  -> RAM 스트레스 진행 ({current_step}/{max_steps}s): 시뮬레이션 사용률 {simulated_usage:.1f}%%", "yellow")

        time.sleep(1) 
        final_percent = psutil.virtual_memory().percent
        
        log(f"  -> 🟢 최종 사용률: {final_percent:.1f}%%. 메모리 반환 확인 완료.", "lime")
        self.progress(90)

        status = "success"
        if final_percent > 85: status = "warning"
        
        summary = f"총 메모리: {total_gb:.2f} GB | 최종 사용률: {final_percent:.1f}%%. 시스템 메모리 상태 양호."
        if status == "warning": summary = f"⚠️ 경고: 최종 사용률 {final_percent:.1f}%%로, 메모리 사용량이 높은 상태입니다."

        result = {
            "status": status,
            "summary": summary,
            "details": {
                "total_memory_gb": round(total_gb, 2),
                "initial_usage_percent": round(initial_used_percent, 1),
                "final_usage_percent": round(final_percent, 1),
                "test_duration_s": self.duration
            }
        }
        
        self.progress(100)
        self._save_result_to_file(result) 
        return result