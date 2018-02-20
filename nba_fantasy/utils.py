from nba_stats.models import (TraditionalSplit, AdvancedSplit, MiscSplit,
                              ScoringSplit, UsageSplit, TrackingBoxScore,
                              FourFactorsBoxScore, HustleStatsBoxScore, Transaction, Player)
from nba_fantasy.forms import (TraditionalScoringForm, AdvancedScoringForm,
                               MiscScoringForm, ScoringScoringForm, UsageScoringForm,
                               TrackingScoringForm, FourFactorsScoringForm, HustleScoringForm,
                               TransactionSettingsForm, ScheduleSettingsForm, DraftSettingsForm,
                               ScoringSettingsForm, RosterSettingsForm)


def get_all_league_forms():
    all_forms = {'transaction': TransactionSettingsForm(),
                 'schedule': ScheduleSettingsForm(),
                 'draft': DraftSettingsForm(),
                 'scoring_options': ScoringSettingsForm(),
                 'roster': RosterSettingsForm()}
    return all_forms


def get_all_scoring_forms():
    all_forms = {  # 'base': BaseScoringForm(),
                  'traditional': TraditionalScoringForm(),
                  'advanced': AdvancedScoringForm(),
                  'misc': MiscScoringForm(),
                  'scoring': ScoringScoringForm(),
                  'usage': UsageScoringForm(),
                  'tracking': TrackingScoringForm(),
                  'four_factors': FourFactorsScoringForm(),
                  'hustle': HustleScoringForm()}

    return all_forms


def convert_field_to_literal(field):
    return field.split("__")[-1].replace("_", " ").replace("pct", "%").upper()


def sort_fields(fields_to_sort):
    all_fields = ([f.name for f in TraditionalSplit._meta.get_fields()] +
                  [f.name for f in AdvancedSplit._meta.get_fields()] +
                  [f.name for f in MiscSplit._meta.get_fields()] +
                  [f.name for f in ScoringSplit._meta.get_fields()] +
                  [f.name for f in UsageSplit._meta.get_fields()] +
                  [f.name for f in TrackingBoxScore._meta.get_fields()] +
                  [f.name for f in FourFactorsBoxScore._meta.get_fields()] +
                  [f.name for f in HustleStatsBoxScore._meta.get_fields()])
    return sorted(fields_to_sort, key=lambda field: all_fields.index(field.split("__")[-1]))


