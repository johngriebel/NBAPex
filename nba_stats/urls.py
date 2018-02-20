from django.conf.urls import url
from nba_stats import views, ajax_views

urlpatterns = [url(r'^$', views.index, name='index'),
               url(r'^admin_portal', views.admin_portal, name='admin_portal'),
               url(r'^players/$', views.players, name='players'),
               url(r'^player/(?P<id>[0-9]+)$', views.player, name='player'),
               url(r'^teams/$', views.teams, name='teams'),
               url(r'^team/(?P<id>[0-9]+)$', views.team, name='team'),
               url(r'^games/$', views.games, name='games'),
               url(r'^games/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/$',
                   views.games, name='games-date'),
               url(r'^user_query/$', views.user_query, name='user-query'),
               url(r'^shot_chart/$', views.shot_chart, name='shot-chart'),
               url(r'^roster_history/$', views.roster_history, name='roster-history'),
               url(r'^download_user_query_results/(?P<fmt>[a-z]+)/$',
                   views.download_user_query_results, name="download-user-query-result"),
               # Begin AJAX calls
               url(r'^ajax/get_player_shot_chart_data/$', ajax_views.get_player_shot_chart_data,
                   name='get-player-shot-chart-data'),
               url(r'^ajax/get_team_roster_history/$', ajax_views.get_team_roster_history,
                   name='get-team-roster-history'),
               url(r'^ajax/get_related_models/$', ajax_views.ajax_get_related_models,
                   name="ajax-get-related-models"),
               url(r'^ajax/send_user_query/$', ajax_views.ajax_send_user_query,
                   name="ajax-send-user-query"),
               url(r'^ajax/get_player_splits/$', ajax_views.ajax_get_player_splits,
                   name="ajax-get-player-splits"),
               url(r'^ajax/get_team_splits/$', ajax_views.ajax_get_team_splits,
                   name="ajax-get-team-splits")
               ]
