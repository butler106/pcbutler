from plugin_base import PCButlerPlugin

class StatisticalSummaryPlugin(PCButlerPlugin):
    plugin_name = "StatisticalSummary"
    description = "진단 결과의 통계 요약을 준비합니다."

    def __init__(self, analysis_id, settings):
        super().__init__(analysis_id, settings)
        self.name = self.plugin_name
        self.description = self.description

    def run(self, logger=None, progress=None, stop_check=None, **kwargs):
        super().run(logger=logger, progress=progress, stop_check=stop_check, **kwargs)
        log = self.logger
        log(f"🔍 '{self.name}' 작업을 시작합니다.", "cyan")
        self.progress(10)

        summary = "통계 요약 프로세스가 시작되었습니다. (실제 분석/집계는 ReportMerge 단계에서 수행)"
        result = {"status": "success", "summary": summary}
        self.progress(100)
        self._save_result_to_file(result)
        return result