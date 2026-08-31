from typing import Dict, Any, Callable, Optional, Union, List 
# ==============================================================================
# 🐍 PC Butler Plugin: 프린터 설정 점검 (PrinterCheck) - 최종 완벽 버전
# - CIM(PowerShell)을 사용하여 프린터 목록과 상세 설정을 안정적으로 조회합니다.
# ==============================================================================
from plugin_base import PCButlerPlugin
import subprocess
import json
import os
import sys

class PrinterCheckPlugin(PCButlerPlugin):
    """
    설치된 Windows 프린터 목록, 기본 프린터 설정 및 공유 상태를 점검합니다.
    """
    plugin_name = "PrinterCheck"
    description = "설치된 프린터 목록, 기본 프린터 설정 및 공유 상태를 점검합니다."
    version = "3.0.0" # 최종 버전

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        # 표준 run 메서드 시작
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        
        log(f"🔍 '{self.name}' 작업을 시작합니다. (프린터 설정 점검)", "cyan")
        self.progress(10)

        # --------------------------------------------------------
        # 1. OS 환경 점검 (Windows 전용)
        # --------------------------------------------------------
        if os.name != "nt":
            summary = "이 플러그인은 Windows 환경에서만 실행 가능합니다."
            log(summary, "yellow")
            self.progress(100)
            return {"status": "warning", "summary": summary}
            
        final_status = "success"
        
        try:
            # --------------------------------------------------------
            # 2. PowerShell 명령 실행 (프린터 목록 JSON 가져오기)
            # --------------------------------------------------------
            log("🔧 Get-CimInstance 명령 실행 중... (프린터 정보 조회)", "white")
            
            # Name, Default(기본 프린터), Shared(공유 여부), PortName, DriverName 필드 포함
            # ConvertTo-Json으로 구조화된 데이터 확보
            ps_script = 'Get-CimInstance -ClassName Win32_Printer | Select-Object Name, Default, Shared, PortName, DriverName | ConvertTo-Json -Compress'
            
            # Subprocess 실행: JSON 출력을 위해 인코딩을 'utf-8'로 설정
            result = subprocess.run(
                ['powershell', '-Command', ps_script], 
                capture_output=True, 
                text=True, 
                check=True, # 실패 시 CalledProcessError 발생
                timeout=20,
                encoding='utf-8',
                errors='ignore'
            )
            
            output = result.stdout.strip()
            self.progress(40)

            # --------------------------------------------------------
            # 3. 결과 파싱 및 분석
            # --------------------------------------------------------
            if not output or output.strip() in ['[]', '{}']:
                summary = "✅ 시스템에 설치된 프린터가 없습니다."
                log(summary, "lime")
                self.progress(100)
                return {"status": "success", "summary": summary, "details": {"total_printers": 0}}

            try:
                # CIM 결과는 객체 배열 형태
                printers = json.loads(output)
            except json.JSONDecodeError:
                error_message = "❌ PowerShell 출력 결과가 JSON 형식이 아닙니다. (데이터 손상 가능성)"
                log(error_message, "red")
                self.progress(100)
                return {"status": "error", "summary": error_message}
            
            total_printers = len(printers)
            default_printer = None
            shared_printers = []
            
            log(f"📝 총 {total_printers}개 프린터 확인됨. 상세 분석 시작.", "white")

            for p in printers:
                name = p.get('Name', '알 수 없음')
                is_default = p.get('Default', False) # True/False (bool)
                is_shared = p.get('Shared', False) # True/False (bool)
                
                if is_default:
                    default_printer = name
                if is_shared:
                    shared_printers.append(name)
                
                log_status = []
                if is_default:
                    log_status.append("기본")
                if is_shared:
                    log_status.append("공유됨")

                log(f"  -> 🖨️ {name} ({', '.join(log_status) if log_status else '일반'}) - 드라이버: {p.get('DriverName', 'N/A')}", "lime" if is_default else "gray")

            self.progress(80)

            # --------------------------------------------------------
            # 4. 최종 결과 보고
            # --------------------------------------------------------
            summary_parts = []
            
            if default_printer:
                summary_parts.append(f"기본 프린터: **{default_printer}**")
            else:
                final_status = "warning"
                summary_parts.append("⚠️ 기본 프린터가 설정되지 않았습니다.")

            if shared_printers:
                # 공유된 프린터가 있는 경우 경고 (보안 이슈)
                final_status = "warning" if final_status == "success" else final_status 
                summary_parts.append(f"⚠️ {len(shared_printers)}개 프린터 공유 중")
                log("⚠️ 프린터 공유는 보안 문제를 일으킬 수 있습니다. 불필요한 공유를 해제하십시오.", "yellow")
            
            if total_printers > 0:
                summary = f"총 {total_printers}개 프린터 확인. " + " | ".join(summary_parts)
                status = final_status
            else:
                summary = "✅ 시스템에 프린터가 설치되어 있지 않습니다."
                status = "success"

            details = {
                "total_printers": total_printers,
                "default_printer": default_printer,
                "shared_printers": shared_printers,
                "all_printers": printers
            }

            self.progress(100)
            return {"status": status, "summary": summary, "details": details}

        except subprocess.CalledProcessError as e:
            # 명령어 실행 실패 (예: 권한 문제, PowerShell 경로 문제)
            error_msg = e.stderr.strip() or "알 수 없는 PowerShell 오류"
            summary = f"❌ 프린터 점검 실패: PowerShell 명령어 실행 오류. ({error_msg})"
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}
        
        except subprocess.TimeoutExpired:
            summary = "❌ 프린터 정보 조회 시간 초과 (Timeout)."
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}
        
        except Exception as e:
            summary = f"❌ 예상치 못한 최종 오류 발생: {type(e).__name__}: {e}"
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}