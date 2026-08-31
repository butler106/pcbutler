from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# plugin_usbscan.py
# 플러그인: USB 연결 기록 점검 (실제 Windows 명령 실행 구조 적용)
import subprocess
import os
import re

class USBScanPlugin(PCButlerPlugin):
    plugin_name = "USB 연결 기록 점검"
    description = "최근 연결된 USB 저장 장치의 기록을 점검하고 장치 정보를 표시합니다. (Windows 전용)"
    
    # 🚨 [필수 수정] def run(...) 함수를 추가하고 실제 로직을 구현합니다.
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.plugin_name}' 작업을 시작합니다. (Windows PnP 장치 기록 조회)", "cyan")
        
        # 1. 플랫폼 체크 (Windows 전용)
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        self.progress(10)
        
        try:
            # 2. PowerShell 명령 실행: 설치된 USB 장치 목록 가져오기
            # 'USB' 클래스의 모든 PnP 장치(메모리, 컨트롤러 등)를 조회합니다.
            command = [
                "powershell", 
                "-Command", 
                "Get-PnpDevice -Class USB | Select-Object FriendlyName, Status"
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8', 
                errors='ignore',
                check=False,
                timeout=30 
            )
            
            output = result.stdout.strip()
            self.progress(50)
            
            # 3. 결과 파싱 및 분석
            usb_devices = []
            # FriendlyName과 Status 패턴을 찾아 파싱
            lines = output.split('\n')
            # 3줄 이후부터 실제 데이터로 간주
            for line in lines[3:]: 
                parts = line.split()
                if len(parts) >= 2:
                    status = parts[-1].strip() # 마지막 단어는 Status
                    name = " ".join(parts[:-1]).strip() # 나머지는 FriendlyName
                    if name and status:
                        usb_devices.append({
                            "name": name,
                            "status": status
                        })

            self.progress(80)

            # 4. 최종 요약
            total_devices = len(usb_devices)
            
            if total_devices == 0:
                summary = "✅ 시스템에 기록된 USB 장치 정보가 거의 없습니다. (양호)"
                status = "success"
                log(summary, "lime")
            else:
                # 'OK' 상태가 아닌 장치 (연결 해제되거나 문제가 있는 장치)를 경고
                non_ok_devices = [d for d in usb_devices if d['status'].upper() != 'OK']
                
                if len(non_ok_devices) > 0:
                    summary = f"⚠️ 총 {total_devices}개의 USB 장치 기록 확인. {len(non_ok_devices)}개의 장치가 비활성/오류 상태입니다. (점검 필요)"
                    status = "warning"
                    log(summary, "yellow")
                else:
                    summary = f"✅ 총 {total_devices}개의 USB 장치 기록 확인. 모두 정상(OK) 상태입니다."
                    status = "success"
                    log(summary, "lime")
                    
            self.progress(100)
            
            # 최종 반환 값에 상세 결과 포함
            return {"status": status, "summary": summary, "details": usb_devices}

        except subprocess.TimeoutExpired:
            error_message = "❌ USB 장치 조회 명령 실행 시간 초과."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}

        except Exception as e:
            error_message = f"❌ USB 연결 기록 점검 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}

    # 🚨 [정리] 기존의 print()를 사용하는 plugin_stop 메서드는 제거하거나 더미로 처리합니다.
    # PCButlerPlugin 베이스 클래스에는 plugin_stop이 없으므로, 제거하거나 pass 처리합니다.
    def plugin_stop(self):
        # 🛑 플러그인 종료는 메인 스케줄러에서 관리합니다.
        pass