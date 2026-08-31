from typing import Dict, Any, Callable, Optional, Union, List
from plugin_base import PCButlerPlugin
import subprocess
import json
import os
import datetime

class PatchStatusPlugin(PCButlerPlugin):
    plugin_name = "PatchStatus"
    description = "설치된 Windows 보안 업데이트 중 최신 항목을 확인합니다."
    version = "3.4.0" # JSON 직렬화 오류 및 필터링 강화 FIX

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger=None, progress=None, stop_check=None, **kwargs):
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        log(f"🔍 '{self.name}' 작업을 시작합니다. (Windows 보안 패치 점검)", "cyan")
        self.progress(1)

        try:
            # InstalledOn을 ISO 8601 포맷으로 강제하여 파싱 오류 방지
            command = (
                'Get-HotFix | '
                'Select-Object HotFixID, Description, @{Name="InstalledOn";Expression={"{0:yyyy-MM-ddTHH:mm:ss}" -f $_.InstalledOn}} | '
                'ConvertTo-Json -Depth 2 | Out-String'
            )
            result = subprocess.run(
                ['powershell', '-Command', command],
                capture_output=True,
                timeout=120
            )

            if stop_check and stop_check():
                log("  -> ⚠️ 보안 패치 점검 중단 요청 수신.", "yellow")
                return {"status": "warning", "summary": "⚠️ 사용자 요청으로 보안 패치 점검 중단됨."}

            output_bytes = result.stdout.strip()
            json_start_index = output_bytes.find(b'[')
            if json_start_index != -1:
                json_data = output_bytes[json_start_index:].decode('utf-8', errors='replace')
            else:
                log("  -> ❌ JSON 데이터 시작점을 찾을 수 없습니다. (HotFix 0개 예상)", "red")
                json_data = "[]" 

            hotfixes = []
            if json_data.strip():
                try:
                    hotfixes = json.loads(json_data.strip())
                except json.JSONDecodeError as jde:
                    log(f"  -> ❌ JSON 파싱 오류 발생. 오류: {jde}", "red")
                    hotfixes = []

            self.progress(30)
            
            # 1. 날짜 파싱 및 HotFix 필터링
            all_hotfixes = [] 
            for fix in hotfixes:
                date_str = fix.get('InstalledOn', '')
                
                try:
                    # ISO 8601 형식으로 파싱
                    fix['InstalledOn_DT'] = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                    all_hotfixes.append(fix)
                except Exception:
                    # 날짜 파싱 실패 시 제외
                    continue
            
            total_count = len(all_hotfixes) # 날짜 파싱에 성공한 업데이트 총 개수
            
            # 2. 보안 패치 필터링
            security_hotfixes = []
            for fix in all_hotfixes:
                description = fix.get('Description', '')
                
                # Description에 Security/보안 업데이트 포함, 또는 HotFixID가 KB로 시작하는 항목 포함
                is_security_update = (
                    'Security Update' in description or 
                    '보안 업데이트' in description or
                    fix.get('HotFixID', '').startswith('KB')
                )

                if is_security_update:
                    security_hotfixes.append(fix)

            self.progress(70)
            
            latest_security_patch = None
            total_security_count = len(security_hotfixes)
            
            if security_hotfixes:
                # 보안 패치만 대상으로 최신 항목을 정렬
                security_hotfixes.sort(key=lambda x: x['InstalledOn_DT'], reverse=True)
                latest_security_patch = security_hotfixes[0]


            if latest_security_patch:
                hotfix_id = latest_security_patch.get('HotFixID', 'N/A')
                installed_on = latest_security_patch['InstalledOn_DT'].strftime('%Y-%m-%d')
                
                # ✅ CRITICAL FIX: datetime 객체를 문자열로 변환하여 JSON 직렬화 오류 방지
                json_safe_latest_patch = latest_security_patch.copy()
                json_safe_latest_patch['InstalledOn_DT'] = json_safe_latest_patch['InstalledOn_DT'].isoformat()
                
                summary = f"✅ 총 {total_security_count}개 보안 패치 확인. 가장 최근 패치: **{hotfix_id}** (설치 날짜: {installed_on})"
                log(summary, "lime")
                status = "success"
                details = {
                    "total_security_patches": total_security_count, 
                    "latest_security_patch": json_safe_latest_patch, # 수정된 사본 사용
                    "all_hotfixes_count": total_count
                }
            else:
                # 경고 문구
                if total_security_count == 0:
                    summary = f"⚠️ 설치된 Windows 보안 패치 기록이 없습니다. (총 {total_count}개 업데이트 중 보안 관련 업데이트 0개)."
                else:
                     summary = f"⚠️ 보안 관련 업데이트는 있으나, 최신 항목의 날짜를 확인하지 못했습니다. (총 {total_security_count}개 업데이트)."
                     
                log(summary, "yellow")
                status = "warning"
                details = {"total_security_patches": total_security_count, "all_hotfixes_count": total_count}

            final_result = {"status": status, "summary": summary, "details": details}
            self.progress(100)
            # PatchStatus 결과 저장 시 TypeError 발생하지 않음
            self._save_result_to_file(final_result) 
            return final_result

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('cp949', errors='ignore').strip() or "알 수 없는 PowerShell 오류"
            summary = f"❌ PowerShell 명령어 실행 오류. ({error_msg})"
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}

        except subprocess.TimeoutExpired:
            summary = "❌ 보안 패치 점검 시간 초과 (120초)."
            log(summary, "red")
            self.progress(100)
            return {"status": "error", "summary": summary}

        except Exception as e:
            error_message = f"❌ 치명적인 오류 발생: {type(e).__name__}: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "FATAL_ERROR", "summary": error_message}