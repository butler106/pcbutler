from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_antiviruscheck.py
# 플러그인: 기관 백신 상태 및 정의 업데이트 점검 (v1.2 - 실시간 감시 로직 수정)
import subprocess
from datetime import datetime, timedelta
import os
import sys
import io
import re

# 콘솔 인코딩 문제 방지 (필요하다면 추가)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass # detach가 불가능한 환경일 경우 무시

class AntivirusCheckPlugin(PCButlerPlugin):
    plugin_name = "기관 백신 상태 점검"
    description = "설치된 백신의 실시간 보호 여부와 정의 업데이트 날짜를 점검합니다."

    # 🚨 [핵심 수정] run 메서드에 실시간 감시 초점 로직 적용
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger

        log("🔍 '기관 백신 상태 점검' 작업을 시작합니다. (실시간 감시 개수 확인)", "cyan")

        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        final_status = "success"
        
        try:
            # WMI SecurityCenter2에서 displayName, productState, timestamp를 '이름;상태;날짜' 문자열로 가져옴
            # NOTE: 날짜 정보는 SecurityCenter2에 없을 수 있으므로 productState만 필수적으로 사용
            cmd = "powershell.exe -Command \"Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | Select-Object -Property displayName, productState, timestamp | ForEach-Object {\\\"$($_.displayName);$($_.productState);$($_.timestamp)\\\"}\""
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                encoding='cp949', # 한국어 환경 기본 인코딩
                startupinfo=startupinfo,
                timeout=10
            )
            
            self.progress(50)
            
            output_lines = result.stdout.strip().split('\n')
            active_av_list = []
            
            for line in output_lines:
                if not line.strip(): continue
                try:
                    parts = line.strip().split(';', 2)
                    if len(parts) < 2: continue
                    name, state_str, update_date_str = parts[0], parts[1], (parts[2] if len(parts) == 3 else None)
                    name = name.strip()
                    
                    state = int(state_str.strip())
                    
                    # 🚨 [핵심 로직] 실시간 감시 활성 여부 판단:
                    # productState의 0x1000 (4096) 비트 (Realtime protected) 또는 
                    # 0x40000 (262144) 비트 (Enabled)를 체크하여 활성 상태로 간주
                    is_realtime_enabled = (state & 0x1000) != 0 
                    is_enabled_overall = (state & 0x40000) != 0 
                    
                    if is_realtime_enabled or is_enabled_overall: 
                         active_av_list.append(name)
                         log(f"  -> 🔍 백신 감지: {name} (State: {state_str} - 실시간 감시 활성 추정)", "gray")
                    else:
                         log(f"  -> 🔍 백신 감지: {name} (State: {state_str} - 비활성 추정)", "gray")

                except Exception as e:
                    log(f"⚠️ 백신 정보 처리 중 오류: {e} (Raw: {line.strip()})", "red")
                    
            # 2. 🚨 [수정된 로직] 실시간 감시 백신 개수 판단 (사용자 요청 1)
            if len(active_av_list) == 1:
                av_name = active_av_list[0]
                # 사용자 요청 포맷: 실시간 감시 __[백신명]하고 통과
                final_summary = f"✅ 실시간 감시 **{av_name}** 작동 중. 상태 양호."
                log(final_summary, "lime")
                final_status = "success"
            elif len(active_av_list) == 0:
                final_summary = "❌ 실시간 감시 백신이 감지되지 않았습니다. 보안 위험!"
                final_status = "error" 
                log(final_summary, "red")
            else: # len(active_av_list) >= 2
                active_names = ', '.join(active_av_list)
                final_summary = f"⚠️ 실시간 감시 백신이 **{len(active_av_list)}개** ({active_names}) 감지되었습니다. 충돌 가능성이 있습니다."
                final_status = "warning"
                log(final_summary, "yellow")
                
            self.progress(100)
            return {"status": final_status, "summary": final_summary}
            
        except subprocess.CalledProcessError as e:
            error_message = f"❌ PowerShell 명령 실행 실패 (코드: {e.returncode})"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
            
        except Exception as e:
            error_message = f"❌ 백신 점검 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}