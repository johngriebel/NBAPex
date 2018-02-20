import random
from decimal import getcontext, Decimal
from nba_fantasy.forms import (TraditionalScoringForm, AdvancedScoringForm, MiscScoringForm,
                               ScoringScoringForm, UsageScoringForm, TrackingScoringForm,
                               FourFactorsScoringForm, HustleScoringForm)


def create_random_scoring_fields():
    getcontext().prec = 4
    scoring_dict = {}
    form_types = [TraditionalScoringForm, AdvancedScoringForm, MiscScoringForm,
                  ScoringScoringForm, UsageScoringForm, TrackingScoringForm,
                  FourFactorsScoringForm, HustleScoringForm]
    fields = []
    for ftype in form_types:
        fields += [fld for fld in ftype().fields]

    chosen_fields = random.sample(fields, 10)
    for fld in chosen_fields:
        scoring_dict[fld] = Decimal(str(random.uniform(-2, 2))[:4])

    return scoring_dict