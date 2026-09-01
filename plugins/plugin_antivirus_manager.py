from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_antivirus_manager.py
# 플러그인: 중복 백신 관리 도구 (v2.0 - 표준 구조 및 오류 처리 적용)

import subprocess
import os
import sys

# 콘솔 인코딩 문제 방지
try:
    import io
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except:
    pass

class AntivirusManagerPlugin(PCButlerPlugin):
    plugin_name = "중복 백신 관리"
    description = "2개 이상의 백신이 감지될 경우, Windows Defender를 비활성화하는 옵션을 제공합니다."
    version = "2.0.0"

    def get_installed_av(self):
        """WMI를 통해 설치된 백신 목록을 가져옵니다."""
        av_list = []
        try:
            # PowerShell을 통해 SecurityCenter2에서 백신 제품 목록을 가져옴
            cmd = "powershell.exe -Command \"Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | Select-Object -ExpandProperty displayName\""
            
            startupinfo = subprocess.STARTUPINFO()
            # [수정] 창 숨김 옵션을 적용하여 깔끔하게 실행
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # [수정] 인코딩 오류 방지: cp949 디코딩 시도 후 실패 시 무시
            result_bytes = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.PIPE)
            result = result_bytes.decode('cp949', errors='ignore').strip()
            
            if result:
                av_list = [name.strip() for name in result.split('\n') if name.strip()]
        except Exception as e:
            # [수정] print 대신 logger 사용
            self.logger(f"⚠️ 백신 정보 조회 중 오류 발생: {e}", "red")
        return av_list

    def disable_defender_realtime(self):
        """PowerShell을 사용하여 Windows Defender 실시간 감시를 비활성화합니다."""
        try:
            # Set-MpPreference -DisableRealtimeMonitoring $true 명령 (관리자 권한 필요)
            cmd = 'powershell.exe -Command "Set-MpPreference -DisableRealtimeMonitoring $true"'
            
            # 관리자 권한으로 실행되도록 요청
            if os.name == 'nt' and not sys.stdin.isatty(): # GUI가 아닌 콘솔 환경에서 실행 시
                # runas를 통해 관리자 권한을 요청하나, 이는 실제 환경에 따라 다르게 작동할 수 있음
                subprocess.run(['powershell', '-Command', f'Start-Process powershell -Verb RunAs -ArgumentList "{cmd}"'], check=True, creationflags=subprocess.SW_HIDE)
            else:
                 subprocess.run(cmd, shell=True, check=True, creationflags=subprocess.SW_HIDE)
            
            return True
        except subprocess.CalledProcessError as e:
            self.logger(f"❌ Windows Defender 비활성화 실패. (관리자 권한 부족 또는 정책 문제): {e}", "red")
            return False
        except Exception as e:
            self.logger(f"❌ Windows Defender 비활성화 중 예외 발생: {e}", "red")
            return False

    # 🚨 [핵심 수정] execute_plugin 대신 run 메서드를 사용하고, 표준 인자를 받도록 변경
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🛡️ '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        self.progress(10)
        
        final_status = "success"
        final_summary = "중복 백신 관리 점검 완료."
        
        try:
            installed_av = self.get_installed_av()
            av_count = len(installed_av)
            log(f"   -> 감지된 백신 수: {av_count}개", "white")
            self.progress(30)
            
            if av_count == 0:
                final_summary = "✅ 설치된 백신이 감지되지 않았습니다. (Windows Defender 비활성화 가능성 있음)"
                log(final_summary, "lime")
                self.progress(100)
                return {"status": "success", "summary": final_summary}
            
            log(f"   -> 설치된 백신 목록: {', '.join(installed_av)}", "white")
            self.progress(50)
            
            if av_count == 1:
                final_summary = "✅ 백신이 1개만 설치되어 있어 중복 충돌 가능성이 낮습니다."
                log(final_summary, "lime")
                self.progress(100)
                return {"status": "success", "summary": final_summary}
                
            # 2개 이상 백신 감지 (av_count >= 2)
            log("   ⚠️ 2개 이상의 백신이 감지되었습니다. 충돌 방지 조치가 필요합니다.", "yellow")
            is_defender_installed = any("defender" in name.lower() for name in installed_av)
            
            if not is_defender_installed:
                final_summary = "⚠️ Windows Defender가 아닌 제3자 백신들이 중복 설치되었습니다. 수동 삭제를 권장합니다."
                log(final_summary, "yellow")
                log("   -> 안전을 위해 직접 '프로그램 추가/제거'에서 사용하지 않는 백신을 삭제해주세요.", "yellow")
                self.progress(100)
                final_status = "warning"
            else:
                # Windows Defender가 포함된 경우 비활성화 옵션 제공 (사용자 입력 요구)
                log("   ℹ️ Windows Defender가 포함되어 있습니다. 충돌 방지를 위해 비활성화 옵션을 제공합니다.", "white")
                log("\n[조치 옵션]", "white")
                log("  Kaspersky와 같은 제3자 백신 사용 시, Windows Defender와 충돌을 막기 위해", "gray")
                log("  실시간 감시 기능을 비활성화하는 것이 좋습니다.", "gray")
                log("\n  [1] Windows Defender 실시간 감시 비활성화 (권장)", "yellow")
                log("  [2] 아무 작업 안 함", "white")
                
                choice_made = False
                while not choice_made:
                    try:
                        # NOTE: 콘솔 환경에서 직접 input() 사용
                        choice = input("  선택할 작업의 번호를 입력하세요: ") 
                        if choice == '1':
                            if self.disable_defender_realtime():
                                log("   ✅ Windows Defender 실시간 감시가 비활성화되었습니다. (재부팅 후 적용될 수 있음)", "lime")
                                final_summary = "중복 백신 충돌 방지를 위해 Windows Defender가 비활성화되었습니다."
                                final_status = "success"
                            else:
                                final_summary = "⚠️ Windows Defender 비활성화에 실패했습니다. 수동 조치가 필요합니다."
                                final_status = "warning"
                            choice_made = True
                        elif choice == '2':
                            final_summary = "ℹ️ 사용자가 작업을 취소했습니다. 수동으로 충돌 방지 조치(백신 삭제 또는 비활성화)를 해주세요."
                            log(final_summary, "white")
                            final_status = "warning"
                            choice_made = True
                        else:
                            log("   -> 잘못된 입력입니다. 1 또는 2를 입력해주세요.", "red")
                    except KeyboardInterrupt:
                        final_summary = "\nℹ️ 사용자가 입력을 중단했습니다. 아무 작업도 수행하지 않습니다."
                        log(final_summary, "white")
                        final_status = "warning"
                        choice_made = True
                
            log(f"   ⭐'{self.plugin_name}' 작업을 완료했습니다. 상태: {final_status.upper()}", "lime" if final_status == "success" else "yellow")
            self.progress(100)

            # 🚨 [필수] 최종 결과 반환
            return {"status": final_status, "summary": final_summary}
            
        except Exception as e:
            error_message = f"❌ 중복 백신 관리 중 치명적인 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}
            
    # 🚨 [수정] plugin_stop은 정리 작업만 수행하도록 변경
    def plugin_stop(self):
        self.logger("🛑 중복 백신 관리 플러그인 종료됨", "gray")
        pass