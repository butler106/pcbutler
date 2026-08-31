from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_browsercheck.py
# 플러그인: 기본 및 사용 브라우저 점검 (기능 구현 완료)
import subprocess
import re
import psutil

class BrowserCheckPlugin(PCButlerPlugin):
    plugin_name = "브라우저 설정 및 사용 점검"
    description = "기본 브라우저 설정과 현재 사용 중인 브라우저를 함께 점검합니다."

    def get_default_browser(self):
        """
        Windows 레지스트리를 쿼리하여 기본 브라우저의 ProgId를 가져오고 이름을 반환합니다.
        PowerShell을 사용하여 Windows 10/11 환경의 기본 브라우저 정보를 조회합니다.
        """
        try:
            # 기본 HTTP 프로토콜 핸들러의 ProgId를 조회하는 PowerShell 명령어
            cmd = 'powershell.exe -Command "Get-ItemPropertyValue -Path HKCU:\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice -Name ProgId"'
            # 텍스트 인코딩을 지정하여 출력을 깔끔하게 처리
            prog_id = subprocess.check_output(cmd, shell=True, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore').strip()
            
            # ProgId를 사람이 읽기 쉬운 이름으로 변환
            if "Chrome" in prog_id:
                return "Google Chrome"
            elif "Edge" in prog_id or "MSEdge" in prog_id:
                return "Microsoft Edge"
            elif "Firefox" in prog_id:
                return "Mozilla Firefox"
            elif "IE" in prog_id:
                return "Internet Explorer"
            elif "Whale" in prog_id:
                return "Naver Whale"
            else:
                return f"알 수 없는 브라우저 ({prog_id})"
        except Exception:
            # 레지스트리 경로 접근 실패 또는 기타 오류 발생 시
            return "정보를 확인할 수 없음 (PowerShell 오류 또는 경로 없음)"

    def get_running_browsers(self):
        """
        psutil을 사용하여 현재 실행 중인 프로세스 목록에서 브라우저를 감지합니다.
        """
        # 일반적인 브라우저 실행 파일 목록 (소문자 기준)
        browser_exes = [
            "chrome.exe", "msedge.exe", "firefox.exe", "iexplore.exe", 
            "opera.exe", "brave.exe", "whale.exe", "safari.exe"
        ]
        running_browsers = set()
        
        # 모든 실행 중인 프로세스를 반복하며 이름 확인
        for proc in psutil.process_iter(['name']):
            try:
                process_name = proc.info['name'].lower()
                
                if process_name in browser_exes:
                    # 일관된 이름으로 저장
                    if "chrome" in process_name:
                        running_browsers.add("Google Chrome")
                    elif "msedge" in process_name:
                        running_browsers.add("Microsoft Edge")
                    elif "firefox" in process_name:
                        running_browsers.add("Mozilla Firefox")
                    elif "whale" in process_name:
                        running_browsers.add("Naver Whale")
                    else:
                        # 기타 브라우저는 실행 파일 이름의 앞부분을 활용
                        running_browsers.add(process_name.replace(".exe", "").title())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # 종료된 프로세스나 접근 불가 프로세스는 무시
                continue
        
        return list(running_browsers)

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 
        self.logger(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
        
        try:
            # 1. 기본 브라우저 점검
            self.progress(30)
            default_browser = self.get_default_browser()
            self.logger(f"  -> 🌐 기본 브라우저: {default_browser}", "lime")

            # 2. 실행 중인 브라우저 점검
            self.progress(60)
            running_browsers = self.get_running_browsers()
            
            # 3. 결과 요약
            if running_browsers:
                self.logger(f"  -> 💻 실행 중인 브라우저 ({len(running_browsers)}개) 목록:", "lime")
                for browser in running_browsers:
                    self.logger(f"     - {browser}", "lime")
                
                # 최종 상태 결정
                summary = f"기본 브라우저: {default_browser}, 실행 중인 브라우저: {len(running_browsers)}개 확인 완료."
                status = "SUCCESS"
            else:
                self.logger("  -> 💻 실행 중인 브라우저가 감지되지 않았습니다.", "yellow")
                summary = f"기본 브라우저: {default_browser} 확인 완료. 실행 중인 브라우저 없음."
                # 실행 중인 브라우저가 없는 것은 문제가 아니므로 SUCCESS/INFO 상태로 처리
                status = "SUCCESS" 

            self.logger(f"✅ [완료] {self.plugin_name} : {summary}", "lime")
            self.progress(100)
            return {"status": status, "summary": summary}
        
        except Exception as e:
            error_summary = f"브라우저 점검 중 예상치 못한 오류 발생: {e}"
            self.logger(f"❌ [오류] {self.plugin_name} : {error_summary}", "red")
            self.progress(100)
            # 오류 발생 시 ERROR 상태 반환
            return {"status": "ERROR", "summary": error_summary}