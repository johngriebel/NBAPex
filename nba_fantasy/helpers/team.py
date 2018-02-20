import logging
from collections import defaultdict
from datetime import date
from nba_stats.models import PlayerTraditionalBoxScore
from nba_stats.utils import get_model, determine_season_for_date, make_season_str
from nba_fantasy.models import (FantasyLineupEntry,
                                FantasyTeamRosterEntry)
from nba_fantasy.constants import POSITION_ORDER
log = logging.getLogger('fantasy')


class LineupEntryRow:
    def __init__(self, position, lup_date, scoring_settings, entry=None):
        # TODO: Right now scoring fields will come out in random order.
        # Maybe we can assign an ordering at creation of scoring settings?
        self.position = position
        self.display_position = POSITION_ORDER.get(position)[1]
        self.matchup = ""
        self.matchup_status = ""
        if entry is None:
            self.player = "None"
            self.player_id = 0
            self.team = "N/A"
            self.eligibility_classes = " ".join(["elig-" + str(x) for x in
                                                 POSITION_ORDER.get(position)[2]])
            for fld in scoring_settings.scoring_fields_vals:
                setattr(self, fld, "")
        else:
            self.player = entry.player.display_first_last
            self.player_id = entry.player.id
            self.team = entry.player.team.abbreviation
            self.eligibility_classes = " ".join(["elig-" + x for x in
                                                 entry.player.numbered_positions.split(",")[:-1]])
            base_box_score = PlayerTraditionalBoxScore.objects.filter(player=entry.player,
                                                                      game__game_date_est=lup_date)
            if base_box_score.exists():
                self.matchup = base_box_score.first().matchup
                self.matchup_status = base_box_score.first().game.game_status_text

            split_fields_dict = defaultdict(list)

            for fld in scoring_settings.scoring_fields_vals:
                split_type, field = fld.split("__")
                split_fields_dict[split_type].append(field)

            for split_type in split_fields_dict:
                fields = split_fields_dict[split_type]
                if split_type in ['PlayerTracking', 'PlayerFourFactors', 'PlayerHustleStats']:
                    suffix = "BoxScore"
                    for fld in fields:
                        setattr(self, split_type + "__" + fld, "TODO")
                    continue
                else:
                    suffix = "Split"
                model = get_model(middle=split_type, suffix=suffix)

                year = determine_season_for_date(lup_date)
                season = make_season_str(year)
                season_long_vals = model.objects.filter(season_id=year,
                                                        player=entry.player,
                                                        season_type="Regular Season",
                                                        per_mode="PerGame",
                                                        group_set="Overall",
                                                        group_value=season).values(*fields)

                if season_long_vals.exists():
                    split = season_long_vals.first()
                    for fld in fields:
                        log.debug((split_type, fld, split[fld]))
                        setattr(self, split_type + "__" + fld, split[fld])


def create_lineup_entry_rows(fantasy_team, scoring_settings, lineup_date=None):
    if lineup_date is None:
        lineup_date = date.today()

    ros_settings = RosterSettings.objects.get(league=fantasy_team.league)
    lineup_entries = FantasyLineupEntry.objects.filter(team=fantasy_team,
                                                       lineup_date=lineup_date)
    if not lineup_entries.exists():
        log.debug("No lineup for this date: {d}. Creating a blank one.".format(d=lineup_date))
        new_entries = []
        roster = FantasyTeamRosterEntry.objects.filter(team=fantasy_team,
                                                       end_date__isnull=True)
        for entry in roster:
            new_lup = FantasyLineupEntry(team=fantasy_team,
                                         player=entry.player,
                                         position="bench",
                                         lineup_date=lineup_date)
            new_entries.append(new_lup)
        FantasyLineupEntry.objects.bulk_create(new_entries)
    lup_entry_list = []
    for fld in sorted(ros_settings.get_nonzero_fields(), key=lambda x: POSITION_ORDER.get(x)[0]):
        if fld != "total":
            log.debug(("FLD", fld))
            num_allowed = getattr(ros_settings, fld)
            entries = lineup_entries.filter(position=fld)
            log.debug(("entry count", entries.count(), "num_allowed", num_allowed))
            for entry in entries:
                log.debug("Adding a real lineup entry")
                lup_entry_list.append(LineupEntryRow(position=entry.position,
                                                     lup_date=lineup_date,
                                                     scoring_settings=scoring_settings,
                                                     entry=entry))

            diff = num_allowed - entries.count()
            for count in range(entries.count(), diff + 1):
                log.debug("Adding a blank row")
                lup_entry_list.append(LineupEntryRow(position=fld,
                                                     lup_date=lineup_date,
                                                     scoring_settings=scoring_settings))

    return lup_entry_list


