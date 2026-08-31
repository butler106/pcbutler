from typing import Dict, Any, Callable, Optional, Union, List 
from plugin_base import PCButlerPlugin
# -*- coding: utf-8 -*-
# 플러그인: 보고서 전송 (Final Stable Version)

import sys
import io
import os
import smtplib
import configparser
import glob # 파일 검색을 위해 glob 모듈 추가
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from datetime import datetime

# 콘솔 인코딩 문제 방지
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')
except:
    pass

class ReportsendPlugin(PCButlerPlugin):
    """
    진단 결과 보고서 파일을 이메일로 자동 전송하는 플러그인입니다.
    """
    # 🚨 [최종 반영] PC Butler 플러그인 필수 속성 추가
    plugin_name = "보고서 전송"
    description = "진단 완료된 보고서 파일(HTML, PDF, ZIP 등)을 이메일로 자동 전송합니다."
    version = "2.1.0"

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        
        # BASE_DIR을 설정하여 경로를 안정화합니다.
        base_path = self.settings.get("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_path = os.path.join(base_path, "config", "config.ini")
        self.report_dir = os.path.join(base_path, "reports")
        self.name = self.plugin_name
        
    def run(self, logger: Optional[Callable] = None, progress: Optional[Callable] = None, stop_check: Optional[Callable] = None, **kwargs) -> Dict[str, Union[str, List[str], Any]]:
        """플러그인의 메인 실행 로직"""
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        self.progress(10)

        log(f"🔍 '{self.name}' 작업을 시작합니다. (SMTP 전송)", "cyan")

        # 1. config.ini 설정 로드
        config = configparser.ConfigParser()
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            config.read(self.config_path, encoding='utf-8')
            
            # 💡 [보강] settings 섹션에서 전송 정보 로드
            smtp_server = config.get("Reportsend", "smtp_server")
            smtp_port = config.getint("Reportsend", "smtp_port", fallback=587)
            smtp_user = config.get("Reportsend", "smtp_user")
            smtp_password = config.get("Reportsend", "smtp_password")
            sender_email = config.get("Reportsend", "sender_email")
            receiver_email = config.get("Reportsend", "receiver_email")
            
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            error_message = f"❌ 이메일 설정 로드 실패: config.ini [Reportsend] 섹션의 필수 항목이 누락되었습니다. ({e})"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
        except FileNotFoundError as e:
            error_message = f"❌ 설정 파일 없음: {e}. config/config.ini 경로 및 파일 존재 여부를 확인하십시오."
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}
        except Exception as e:
            error_message = f"❌ 설정 로드 중 예상치 못한 오류 발생: {e}"
            log(error_message, "red")
            self.progress(100)
            return {"status": "error", "summary": error_message}

        self.progress(30)
        
        # 2. 이메일 메시지 구성
        msg = EmailMessage()
        msg['Subject'] = f'[PC Butler] 진단 보고서 - ID:{self.analysis_id}'
        msg['From'] = sender_email
        msg['To'] = receiver_email
        
        body = f"""
        PC Butler 시스템 진단 보고서가 첨부되었습니다.
        
        - 진단 ID: {self.analysis_id}
        - 진단 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        - 상세 내용은 첨부된 파일을 확인해 주십시오.
        
        *본 메일은 PC Butler 플러그인에 의해 자동 발송되었습니다.*
        """
        msg.set_content(body)
        log(f"  -> 수신자: {receiver_email}", "white")

        # 3. 보고서 파일 첨부 (Analysis_Report_{analysis_id}* 파일 검색)
        report_filename_base = f"Analysis_Report_{self.analysis_id}"
        # reports 폴더에서 해당 ID로 시작하는 모든 파일 검색 (html, pdf, zip 등)
        file_paths = glob.glob(os.path.join(self.report_dir, f"{report_filename_base}.*"))
        
        if not file_paths:
            log(f"  -> ⚠️ 첨부할 보고서 파일({report_filename_base}.*)을 찾을 수 없습니다. 전송을 계속합니다.", "yellow")
        
        for file_path in file_paths:
            try:
                # 파일 MIME 타입 추측
                import mimetypes
                mimetype, encoding = mimetypes.guess_type(file_path)
                if mimetype is None:
                    maintype = 'application'
                    subtype = 'octet-stream'
                else:
                    maintype, subtype = mimetype.split('/')
                    
                with open(file_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(file_path))
                
                log(f"  -> ✅ 첨부 완료: {os.path.basename(file_path)}", "lime")
            except Exception as e:
                log(f"  -> ⚠️ 첨부 실패 ({os.path.basename(file_path)}): {e}", "yellow")
        
        self.progress(70)

        # 4. 이메일 전송
        log("🚀 이메일 서버에 연결 및 전송 시도...", "white")
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls() # TLS 암호화 사용
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            summary = f"✅ 보고서가 {receiver_email} (으)로 성공적으로 전송되었습니다."
            log(summary, "lime")
            self.progress(100)
            
            # 🚨 [필수] Success 반환
            return {"status": "success", "summary": summary}

        except smtplib.SMTPAuthenticationError:
            error_message = "❌ 이메일 전송 실패: 인증 오류(앱 비밀번호)가 발생했습니다. config.ini의 [Reportsend] 섹션 비밀번호(smtp_password)를 확인하세요."
            log(error_message, "red")
            self.progress(100)
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}
        except Exception as e:
            error_message = f"❌ 이메일 전송 중 예상치 못한 오류 발생: 서버 접속 실패, 네트워크 문제 등. ({e})"
            log(error_message, "red")
            self.progress(100)
            # 🚨 [필수] Error 반환
            return {"status": "error", "summary": error_message}