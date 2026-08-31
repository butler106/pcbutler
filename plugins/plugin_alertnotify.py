# ==============================================================================
# 🐍 PC Butler Plugin: 알림 / 경고 전송 (AlertNotify) - 최종 구조 안정화
# [수정 사항]
# 1. NameError 해결: 'Union', 'List' 타입 임포트 추가.
# 2. TypeError 해결: run() 메서드 시그니처와 super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs) 호출을 'stop_check' 기반으로 변경.
# ==============================================================================
from plugin_base import PCButlerPlugin
# plugin_alertnotify.py
# Butler 알림 플러그인 (v1.4 - NoneType 및 로깅/구조 최종 수정)

# -*- coding: utf-8 -*-
import sys
import io
import os
import json
from datetime import datetime
import smtplib
import configparser
from email.message import EmailMessage
# 🚨 [수정 1]: 'Union', 'List' 타입 힌트 오류 해결을 위해 추가
from typing import Dict, Any, Optional, Callable, Union, List 

# 콘솔 인코딩 문제 방지
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass

class AlertNotifyPlugin(PCButlerPlugin):
    plugin_name = "알림 / 경고 전송"
    description = "오류가 임계값을 초과하면 관리자에게 이메일을 전송하고 로그를 기록합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        
        # Path setup
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.log_path = os.path.join(base_path, "reports", "alert_log.json")
        
        # Email settings (using configparser for robustness)
        self.config = configparser.ConfigParser()
        # config.ini 파일 경로를 settings에서 가져오거나 기본 경로를 사용하도록 수정
        config_path = self.settings.get("CONFIG_PATH", os.path.join(base_path, 'config.ini'))
        if os.path.exists(config_path):
            self.config.read(config_path)
            
    # 🚨 [수정 2]: run 시그니처를 base.py와 통일하고 stop_check를 받도록 변경
    # 부모 클래스의 run 메서드 시그니처와 일치시키고, **kwargs를 추가합니다.
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        
        # 부모 클래스의 run 메서드 호출 (stop_check를 전달)
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        
        if self.logger:
            self.logger(f"🔍 '{self.plugin_name}' 작업을 시작합니다.", "cyan")
            
        # Configuration check
        if 'ALERT' not in self.config:
            self.logger("❌ Alert 설정 섹션(config.ini의 [ALERT])이 없어 알림 플러그인을 건너뜁니다.", "yellow")
            return {
                "status": "WARNING",
                "summary": "Alert 설정 누락으로 건너뜀.",
                "remediation": "config.ini 파일에 [ALERT] 섹션과 'threshold' 값을 설정하십시오."
            }
        
        # Load settings
        alert_config = self.config['ALERT']
        threshold = alert_config.getint('threshold', 5) # 기본 임계값 5회
        email_recipient = alert_config.get('recipient_email', '')
        
        # 1. 이전 알림 로그 확인
        current_error_count = self._get_current_error_count(self.logger)
        
        # progress 함수 호출 시 required 인자인 current_step, total_steps, message 전달
        self.progress(1, 4, f"현재 오류 횟수 확인: {current_error_count} / {threshold}")

        # 2. 임계값 초과 확인
        if current_error_count >= threshold:
            self.logger(f"🚨🚨 오류 횟수({current_error_count}회)가 임계값({threshold}회)을 초과했습니다. 알림 전송을 시도합니다.", "red")
            
            # 3. 이메일 전송
            if email_recipient:
                self.progress(2, 4, "이메일 알림 전송 시도...")
                send_success = self._send_email_notification(email_recipient, self.logger)
                
                if send_success:
                    self.logger("✅ 이메일 알림 전송 완료. 로그를 초기화합니다.", "lime")
                    self._reset_log(self.logger)
                    return {
                        "status": "SUCCESS",
                        "summary": f"오류 임계값({threshold}회) 초과로 관리자에게 알림 이메일 전송 완료.",
                        "remediation": []
                    }
                else:
                    self.logger("❌ 이메일 전송 실패. 설정(SMTP/계정 정보)을 확인하십시오.", "red")
            else:
                self.logger("⚠️ 이메일 수신자 설정이 없어 이메일 알림을 건너뜁니다.", "yellow")
            
            return {
                "status": "WARNING",
                "summary": "오류 임계값 초과. 이메일 전송 실패 또는 설정 누락.",
                "remediation": ["config.ini 파일의 [ALERT] 섹션에 'recipient_email'을 올바르게 설정하십시오."]
            }
            
        else:
            self.logger(f"👍 오류 횟수({current_error_count}회)가 임계값({threshold}회) 미만이므로 알림을 건너뜁니다.", "gray")
            return {
                "status": "SUCCESS",
                "summary": f"오류 횟수({current_error_count}회)가 임계값 미만. 알림 미전송.",
                "remediation": []
            }
            
    # --- Helper Methods ---

    def _send_email_notification(self, recipient_email: str, log: Callable) -> bool:
        """실제 이메일 전송 로직"""
        try:
            email_config = self.config['EMAIL']
            smtp_server = email_config['smtp_server']
            smtp_port = email_config.getint('smtp_port', 587)
            sender_email = email_config['sender_email']
            sender_password = email_config['sender_password']
            
            msg = EmailMessage()
            msg['Subject'] = f'[PC Butler Alert] 임계값 초과 오류 알림 ({self.analysis_id})'
            msg['From'] = sender_email
            msg['To'] = recipient_email
            
            # 알림 로그 내용 첨부
            log_content = self._get_log_content()
            body = f"PC Butler 진단 중 설정된 임계값({self.config['ALERT'].getint('threshold', 5)}회)을 초과한 오류가 발생했습니다.\n\n"
            body += "--- Alert Log ---\n"
            body += log_content
            body += "\n-------------------\n\n조치 바랍니다."
            
            msg.set_content(body)
            
            # SMTP 연결
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # TLS 보안 시작
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            return True
            
        except KeyError:
            log("❌ config.ini에 [EMAIL] 섹션 또는 필수 설정(smtp_server, sender_email 등)이 누락되었습니다.", "red")
            return False
        except Exception as e:
            log(f"❌ 이메일 전송 예외 발생: {e}", "red")
            return False

    def _get_log_content(self) -> str:
        """알림 로그 파일에서 내용을 읽어 문자열로 반환"""
        if not os.path.exists(self.log_path):
            return "알림 로그 파일이 존재하지 않습니다."
        
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                logs: List[Dict[str, Any]] = json.load(f)
            
            content = ""
            for log in logs:
                content += f"[{log.get('timestamp')}] 오류 횟수: {log.get('error_count')} / 상세: {log.get('details', 'N/A')}\n"
            
            return content.strip()
            
        except Exception:
            return "알림 로그 파일을 읽는 데 실패했습니다."

    def _get_current_error_count(self, log: Callable) -> int:
        """알림 로그 파일에서 현재 오류 횟수를 계산"""
        try:
            if not os.path.exists(self.log_path):
                return 0
            
            with open(self.log_path, "r", encoding="utf-8") as f:
                try:
                    logs: List[Dict[str, Any]] = json.load(f)
                    return len(logs)
                except json.JSONDecodeError:
                    log("⚠️ 알림 로그 파일이 손상되었습니다. 초기화합니다.", "yellow")
                    self._reset_log(log)
                    return 0
        except Exception:
            return 0
            
    def _reset_log(self, log: Callable):
        """알림 로그 파일을 삭제하여 카운터를 초기화"""
        try:
            if os.path.exists(self.log_path):
                os.remove(self.log_path)
                log("   -> 알림 로그 파일 초기화 완료.", "gray")
        except Exception as e:
            log(f"❌ 알림 로그 초기화 실패: {e}", "red")

    # 로그 기록 도우미 함수 (로깅 사용)
    def _log_alert(self, error_count: int, error_details: str, log: Callable):
        """오류 발생 시 알림 로그에 기록"""
        try:
            alert_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error_count": error_count,
                "details": error_details,
            }

            logs = []
            if os.path.exists(self.log_path):
                with open(self.log_path, "r", encoding="utf-8") as f:
                    try: 
                        logs = json.load(f)
                    except json.JSONDecodeError: 
                        logs = []
            
            logs.append(alert_entry)

            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=4, ensure_ascii=False)
            
        except Exception as e:
             log(f"❌ 알림 로그 기록 실패: {e}", "red")