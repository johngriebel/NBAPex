from django.apps import AppConfig


class NbaStatsConfig(AppConfig):
    name = 'nba_stats'
    verbose_name = "NBA Stats Application"

    def ready(self):
        import nba_stats.signals