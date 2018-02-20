import logging
from copy import deepcopy
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import CreateView
from django.views.generic.base import TemplateView

from nba_stats.utils import auto_strip_and_convert_fields
from nba_fantasy.models import FantasyTeam, FantasyLeague
from nba_fantasy.forms import FantasyLeagueForm
from nba_fantasy.utils import get_all_scoring_forms, get_all_league_forms
log = logging.getLogger('fantasy')


class IndexView(TemplateView):
    template_name = "nba_fantasy/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        my_teams = []
        user_id = self.request.session.get('user_id')
        if user_id is not None:
            my_teams = FantasyTeam.objects.filter(owner_id=user_id)
        context['my_teams'] = my_teams

        return context


class FantasyLeagueFormView(View):
    form_class = FantasyLeagueForm
    template_name = "nba_fantasy/create_league_single_page.html"

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        context = {'form': form}
        all_scoring_forms = get_all_scoring_forms()
        all_league_forms = get_all_league_forms()
        context.update(all_scoring_forms)
        context.update(all_league_forms)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        log.debug(("REQUEST", request.POST))
        parms = deepcopy(request.POST)
        user = User.objects.get(id=request.session['user_id'])
        parms['commissioner'] = user

        scoring_fields_in_use = {}
        for key in request.POST.keys():
            if "PlayerTraditional__" in key:
                scoring_fields_in_use[key] = request.POST[key] or 0

        parms['scoring_fields_vals'] = scoring_fields_in_use

        # Workaround for bug in Django that tries to submit Booleans as 'on' or 'off'
        for key in parms:
            if 'flag' in key:
                parms[key] = parms[key].lower() == "on"

        league = auto_strip_and_convert_fields(FantasyLeague, data=parms)
        league.save()
        request.session['league_id'] = league.id

        return redirect("nba_fantasy:league-homepage", league_id=league.id)

