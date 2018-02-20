from random import randint, random
from datetime import timedelta
from django.db.models import Max
from factory.fuzzy import BaseFuzzyAttribute


# This is a pseudo sequence I suppose. Using this because there
# Is no guaranteed or sensical order in which the NBA assigns IDs to things
class FuzzyEntityIdentifier(BaseFuzzyAttribute):
    def __init__(self, model, field, **kwargs):
        self.model = model
        self.field = field
        super(FuzzyEntityIdentifier, self).__init__(**kwargs)

    def fuzz(self):
        cur_max_entity_id = self.model.objects.all().aggregate(Max(self.field))
        value = cur_max_entity_id[self.field + "__" + self.field]
        return value + 1


class FuzzyDuration(BaseFuzzyAttribute):
    def __init__(self, min_seconds=0, max_seconds=3600, **kwargs):
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
        super(FuzzyDuration, self).__init__(**kwargs)

    def fuzz(self):
        seconds = randint(self.min_seconds, self.max_seconds)
        return timedelta(seconds=seconds)


class FuzzyNullable(BaseFuzzyAttribute):
    def __init__(self, non_null_type, prob_null=0.5, **kwargs):
        self.non_null_type = non_null_type
        self.prob_null = prob_null
        self.field_args = kwargs
        super(FuzzyNullable, self).__init__(**kwargs)

    def fuzz(self):
        rand_val = random()
        if rand_val >= self.prob_null:
            return None
        else:
            field = self.non_null_type(**self.field_args)
            value = field.fuzz()
            return value


def generate_time_left_in_period_stamp():
    timestamp = str(randint(0, 12)) + ":" + str(randint(0, 60)).rjust(2, "0")
    return timestamp
