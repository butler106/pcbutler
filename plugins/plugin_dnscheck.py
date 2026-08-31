from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: DNS 응답 속도 점검 (Dnscheck) - 안정화 버전
# - Ping 명령어 실행 시 I/O Deadlock 및 디코딩 오류 방지 로직 적용
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import os
import time

class DNSCheckPlugin(PCButlerPlugin):
    """
    외부 DNS 서버에 대한 Ping 테스트를 통해 응답 속도를 점검합니다.
    """
    # 필수 속성
    plugin_name = "Dnscheck"
    description = "Google DNS (8.8.8.8)에 대한 응답 속도를 측정합니다."
    
    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        self.logger(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            self.logger(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        target_ip = "8.8.8.8"
        self.progress(10)
        
        try:
            self.logger(f"  -> 🔍 Ping 테스트 시작 (대상: {target_ip})...", "yellow")
            
            # Ping 명령어 실행 (패킷 4개)
            command = ["ping", "-n", "4", target_ip]
            
            # 🚨 [핵심 수정]: text=True 및 encoding 제거, 바이트로 수신하여 I/O Deadlock 방지
            result = subprocess.run(
                command,
                capture_output=True, # 바이트로 수신
                shell=True,
                check=False,
                timeout=10 
            )
            
            # 🚨 [핵심 수정]: 수동 디코딩 (cp949 우선)
            output = ""
            try:
                # 1차 시도: Windows 기본 인코딩
                output = result.stdout.decode('cp949', errors='ignore').strip()
            except Exception:
                # 2차 시도: 표준 인코딩
                output = result.stdout.decode('utf-8', errors='ignore').strip()
                
            self.logger(f"  -> ℹ️ Ping 결과 로그 (일부): {output[:100]}...", "gray")
            
            self.progress(40)

            # 평균 응답 시간 추출 (ms)
            avg_time = None
            for line in output.split('\n'):
                # '평균' 또는 'Average' 키워드를 포함하는 라인 탐색
                if ("평균" in line or "Average" in line) and "ms" in line:
                    try:
                        # 예: "평균 = 20ms" 또는 "Average = 20ms"
                        # '=' 뒤의 값에서 'ms'를 제거하고 숫자로 변환
                        avg_time_str = line.split('=')[-1].split('ms')[0].strip()
                        # 숫자로만 이루어지도록 정리 (정규식 대신 단순 문자열 치환 사용)
                        avg_time = int("".join(filter(str.isdigit, avg_time_str)))
                        break
                    except:
                        # 파싱 오류 시 무시하고 다음 라인 시도
                        pass
            
            self.progress(70)

            # 최종 상태 판별
            if avg_time is None:
                summary = "❌ Ping 테스트에 실패했거나 결과를 해석할 수 없습니다. (네트워크 연결 확인 필요)"
                status = "error"
                self.logger(f"  -> ❌ 응답 시간 측정 실패.", "red")
            elif avg_time >= 50:
                summary = f"⚠️ DNS 응답 시간: {avg_time}ms. 다소 느립니다. (권장: 30ms 이하)"
                status = "warning"
                self.logger(f"  -> ⚠️ 응답 시간: {avg_time}ms (느림)", "yellow")
            else:
                summary = f"✅ DNS 응답 시간: {avg_time}ms. 상태 양호."
                status = "success"
                self.logger(f"  -> ✅ 응답 시간: {avg_time}ms (양호)", "lime")
            
            self.progress(100)
            
            return {"status": status, "summary": summary, "details": output}

        except Exception as e:
            error_message = f"❌ [오류] DNS 점검 플러그인 실행 실패: {e}"
            self.logger(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}