from django.db import models
from django.core.validators import validate_comma_separated_integer_list
from django.db.models import Count, QuerySet
from django.utils import timezone
from nba_stats.custom_managers import ActivePlayersManager
from nba_stats.constants import REGULAR_SEASON, PLAYOFFS


class BaseModel(models.Model):
    user_exposed = False
    create_ts = models.DateTimeField(default=timezone.now)
    # Might not be a user, but a process, script name, etc.
    create_user = models.CharField(max_length=255)
    mod_ts = models.DateTimeField(null=True)
    mod_user = models.CharField(max_length=255, null=True)

    def save(self, *args, **kwargs):
        if self.id is None:
            self.create_ts = timezone.now()
        else:
            self.mod_ts = timezone.now()

        if hasattr(self, "season_type"):
            if hasattr(self, "career_flag") and "career" in self.season_type.lower():
                self.career_flag = True

            new_season_type = self.season_type
            for junk_str in [" ", "Career", "Totals", "Season"]:
                new_season_type = new_season_type.replace(junk_str, "")

            self.season_type = new_season_type

        super(BaseModel, self).save(*args, **kwargs)

    @classmethod
    def get_related_models(cls, app_names=None):
        class_vars = vars(cls)
        related_sets = [class_vars[v] for v in class_vars if v.endswith("_set")]
        related_models = [cls]
        for rset in related_sets:
            rel_model = rset.rel.related_model
            if app_names is None or (rel_model._meta.app_label in app_names):
                related_models.append(rel_model)
        return related_models

    class Meta:
        abstract = True


# For now, this is a silly stub class, but I'm going to create it
# Because I think there is going to be more stuff I want to add.
class UserExposedModel(BaseModel):
    user_exposed = True

    class Meta:
        abstract = True


class LeagueSeason(BaseModel):
    year = models.IntegerField(unique=True)
    pre_season_start_date = models.DateField()
    regular_season_start_date = models.DateField()
    playoffs_start_date = models.DateField()
    # Unknown for current seasons
    playoffs_end_date = models.DateField(null=True)

    def determine_season_type_for_date(self, date_in_q):
        if not (self.pre_season_start_date <= date_in_q <= self.playoffs_end_date):
            raise ValueError("Invalid date for season {s}".format(s=str(self)))
        if date_in_q >= self.playoffs_start_date:
            return PLAYOFFS
        else:
            return REGULAR_SEASON

    def __str__(self):
        suf = int(str(self.year)[2:])
        suf += 1
        if self.year == 1999:
            season_str = "1999-00"
        elif 2000 <= self.year <= 2008:
            season_str = "%s-%s" % (str(self.year), str(suf).rjust(2, '0'))
        else:
            season_str = "%s-%s" % (str(self.year), str(suf))
        return season_str

    class Meta:
        db_table = 'season'


class Team(UserExposedModel):
    # Should probably rename team_id it's already causing problems
    team_id = models.IntegerField()
    city = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=5)
    conference = models.CharField(max_length=4, null=True)
    division = models.CharField(max_length=25, null=True)
    code = models.CharField(max_length=25, null=True)
    # Why is this commented out?
    # active_flag = models.BooleanField(default = True)
    # Begin new fields. These are made nullable for db purpose, but in practice they should not be
    arena = models.CharField(max_length=100, null=True)
    # For whatever reason, nba.com has this stored as a string. might (read: probably) run into
    # problems here
    arena_capacity = models.IntegerField(null=True)
    owner = models.CharField(max_length=200, null=True)
    general_manager = models.CharField(max_length=200, null=True)
    head_coach = models.ForeignKey("Coach", null=True, blank=True)
    d_league_affiliation = models.CharField(max_length=150, null=True)

    bbref_abbreviation = models.CharField(max_length=5, null=True)

    def __str__(self):
        return "%s %s" % (self.city, self.name)

    class Meta:
        db_table = 'team'


class TeamColorXref(BaseModel):
    team = models.ForeignKey(Team)
    hex_str = models.CharField(max_length=7)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'team_color_xref'
        unique_together = ('team', 'order')


class TeamHistory(BaseModel):
    team = models.ForeignKey(Team)
    city = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    year_founded = models.IntegerField()
    active_thru = models.IntegerField()

    class Meta:
        db_table = 'team_history'


class TeamAward(BaseModel):
    team = models.ForeignKey(Team)
    award_type = models.CharField(max_length=100)
    year_awarded = models.IntegerField()
    opposite_team = models.CharField(max_length=150, null=True)

    class Meta:
        db_table = 'team_award'
        unique_together = ('team', 'award_type', 'year_awarded')


class TeamHof(BaseModel):
    team = models.ForeignKey(Team)
    # Just waiting for this to break on a coach or executive or something
    player = models.ForeignKey("Player")
    position = models.CharField(max_length=50, default="")
    seasons_with_team = models.CharField(max_length=150, default="")
    year_elected = models.IntegerField(null=True)

    class Meta:
        db_table = 'team_hof'
        unique_together = ('team', 'player')


class TeamRetired(BaseModel):
    player = models.ForeignKey("Player", null=True)
    # Should only be populated in the case of player being null
    player_name = models.CharField(max_length=200, null=True)
    # The Orlando Magic retired "The Sixth Man' so this has to be nullable.
    # There really needs to be some damn rules about what numbers you can retire -_-
    position = models.CharField(max_length=50, default="", null=True)
    # Thanks to the stupid Miami Heat and stupid Michael Jordan, this has to be nullable
    seasons_with_team = models.CharField(max_length=150, default="", null=True)
    year_retired = models.IntegerField(null=True)
    jersey = models.CharField(max_length=10, null=True)

    class Meta:
        db_table = 'team_retired'


class Player(UserExposedModel):
    player_id = models.IntegerField(unique=True)
    # Some players go by one name
    first_name = models.CharField(max_length=100, null=True)
    last_name = models.CharField(max_length=100, null=True)
    display_first_last = models.CharField(max_length=201)
    display_last_comma_first = models.CharField(max_length=202, null=True)
    display_fi_last = models.CharField(max_length=102, null=True)
    birthdate = models.DateField(null=True)
    school = models.CharField(max_length=200, null=True)
    country = models.CharField(max_length=200, null=True)
    last_affiliation = models.CharField(max_length=200, null=True)
    height = models.IntegerField(default=0)
    weight = models.IntegerField(default=0)
    season_exp = models.IntegerField(default=0)
    jersey = models.CharField(max_length=10, null=True)
    position = models.CharField(max_length=40, null=True, validators=[])
    rosterstatus = models.CharField(max_length=20, null=True)
    team = models.ForeignKey(Team, null=True)
    # These fields are include because they can change after a player retires.
    # For instance, if a player retired as a Buffalo Brave, simply referencing the fields in the Teams table would list
    # Him as a Los Angeles Clipper which we don't really want
    team_name = models.CharField(max_length=200, null=True)
    team_abbreviation = models.CharField(max_length=3, null=True)
    team_code = models.CharField(max_length=50, null=True)
    team_city = models.CharField(max_length=100, null=True)
    playercode = models.CharField(max_length=100, null=True)
    from_year = models.IntegerField(null=True)
    to_year = models.IntegerField(null=True)
    draft_year = models.CharField(max_length=50, default="", null=True)
    draft_round = models.CharField(max_length=50, default="", null=True)
    draft_number = models.CharField(max_length=50, default="", null=True)
    dleague_flag = models.BooleanField(default=False)
    bbref_id_str = models.CharField(max_length=25, null=True)
    alternate_name = models.CharField(max_length=201, null=True)
    rotoworld_id_str = models.CharField(max_length=100, null=True)
    numbered_positions = models.CharField(max_length=10, null=True,
                                          validators=[validate_comma_separated_integer_list])
    objects = models.Manager()
    active_players = ActivePlayersManager()

    def __str__(self):
        return "%s %s %s %s %s" % (self.display_first_last, self.team_city, self.team_name, str(self.from_year),
                                   str(self.to_year))

    class Meta:
        db_table = 'player'


class Coach(UserExposedModel):
    # bbref str
    coach_id = models.CharField(max_length=50)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    display_first_last = models.CharField(max_length=201)
    birthdate = models.DateField(null=True)
    year_min = models.IntegerField(null=True)
    year_max = models.IntegerField(null=True)
    years = models.IntegerField(null=True)
    school = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.display_first_last

    class Meta:
        db_table = 'coach'
        verbose_name_plural = 'coaches'


class PlayerTeamRosterXref(BaseModel):
    team = models.ForeignKey(Team)
    player = models.ForeignKey(Player)
    season = models.ForeignKey(LeagueSeason, null=True)
    # The fact that '00' is a valid number in the NBA really irritates me.
    # Damn you Robert Parish
    number = models.CharField(max_length=25, default="", null=True)

    class Meta:
        db_table = 'player_team_roster_xref'
        # Note: If I ever come across a case where a player was on a team two separate times
        # In the same season, but wearing a different jersey number, this constraint will have to be
        # Changed. I kind of hope it happens to be honest
        unique_together = ('team', 'player', 'season')


class CoachTeamRosterXref(BaseModel):
    team = models.ForeignKey(Team)
    coach = models.ForeignKey(Coach)
    season = models.ForeignKey(LeagueSeason, null=True)
    coach_type = models.CharField(max_length=50)

    class Meta:
        db_table = 'coach_team_roster_xref'
        unique_together = ('team', 'coach', 'season', 'coach_type')


class PlayerContractSeason(BaseModel):
    player = models.ForeignKey(Player)
    season = models.ForeignKey(LeagueSeason, null=True)
    salary = models.IntegerField()
    # TODO: Make this use choices
    option = models.CharField(max_length=60, null=True)

    class Meta:
        db_table = 'player_contract_season'


class DraftPick(BaseModel):
    year = models.IntegerField()
    pick = models.IntegerField()
    team = models.ForeignKey(Team)
    # Including both fields & allowing player to be null because some guys are picked
    # But don't play in the NBA, or at all for some.
    player = models.ForeignKey(Player, null=True)
    player_name = models.CharField(max_length=200)

    def __str__(self):
        s = "{y};{n};{t};{p}".format(y=self.year, n=self.pick,
                                     t=self.team, p=self.player_name)
        return s

    class Meta:
        db_table = 'draft_pick'


class Transaction(BaseModel):
    player = models.ForeignKey(Player)
    from_team = models.ForeignKey(Team, null=True, related_name="from_team")
    to_team = models.ForeignKey(Team, null=True, related_name="to_team")
    transaction_type = models.CharField(max_length=100)
    transaction_date = models.DateField()
    description = models.TextField()
    # Not quite sure what these next two fields do
    group_sort = models.CharField(max_length=75, null=True)
    additional_sort = models.CharField(max_length=75, null=True)

    def __str__(self):
        s = ": ".join([str(self.transaction_date),
                       self.player.display_first_last,
                       self.description])
        return s

    class Meta:
        db_table = 'transaction'
        unique_together = ('player', 'from_team', 'to_team', 'transaction_date')


class RosterEntry(BaseModel):
    team = models.ForeignKey(Team, null=True)
    player = models.ForeignKey(Player)
    acquired_via = models.CharField(max_length=100)
    acquisition_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    def __str__(self):
        s = ("Roster Entry: {tm}: {plr} "
             "acq. via {acq} on {dt}").format(tm=str(self.team),
                                              plr=self.player.display_first_last,
                                              acq=self.acquired_via,
                                              dt=str(self.acquisition_date))
        return s

    class Meta:
        db_table = 'roster_entry'


class Official(UserExposedModel):
    official_id = models. IntegerField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    jersey_num = models.CharField(max_length=5)

    class Meta:
        db_table = 'official'


class CoachSeason(BaseModel):
    coach = models.ForeignKey(Coach)
    # TODO: Eventually map these from bbref abbreviation to team model instances
    team_id = models.CharField(max_length=10)
    season = models.ForeignKey(LeagueSeason, null=True)
    career_flag = models.BooleanField(default=False)
    g = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    win_loss_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    g_playoffs = models.IntegerField(default=0)
    wins_playoffs = models.IntegerField(default=0)
    losses_playoffs = models.IntegerField(default=0)
    win_loss_pct_playoffs = models.DecimalField(max_digits=10, decimal_places=3, default=0)

    def __str__(self):
        return ";".join([str(self.coach), self.team_id, str(self.season),
                         str(self.wins), str(self.losses)])

    class Meta:
        db_table = 'coach_season'
        unique_together = ("coach", "team_id", "season")


class Season(BaseModel):
    # Value of 0 indicates Career Totals
    season = models.ForeignKey(LeagueSeason, null=True)
    # regular, post, all star
    # Should probably break this out into a separate model like we do with statuses
    season_type = models.CharField(max_length=100)
    team = models.ForeignKey(Team)
    team_abbreviation = models.CharField(null=True, max_length=5)
    per_mode = models.CharField(max_length=50, null=True, default="")
    gp = models.IntegerField(default=0)
    w = models.IntegerField(default=0)
    l = models.IntegerField(default=0)
    w_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    min = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    # Should probably be another class and Foreign Key here
    league_id = models.IntegerField(default=0)

    fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fga = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    fg3m = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg3a = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg3_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    ftm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fta = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ft_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    oreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    reb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ast = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    stl = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    blk = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    tov = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pf = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pts = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    plus_minus = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)

    class Meta:
        abstract = True


class PlayerSeason(Season):
    player = models.ForeignKey(Player)
    player_name = models.CharField(max_length=200)
    player_age = models.IntegerField(null=True)
    career_flag = models.BooleanField(default=False)
    gs = models.IntegerField(default=0, null=True)
    blka = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pfd = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    dd2 = models.IntegerField(default=0, null=True)
    td3 = models.IntegerField(default=0, null=True)

    class Meta:
        db_table = 'player_season'
        unique_together = ("player", "season", "season_type", "team", "per_mode")

    def __str__(self):
        return ("{player}, {season}, {season_type}, {team}, "
                "{points} PPG, {rebounds} RPG, {assists} APG").format(player=self.player_name, season=self.season,
                              season_type=self.season_type, team=self.team_abbreviation,
                              points=self.pts, rebounds=self.reb, assists=self.ast)


class TeamSeason(Season):
    team_city = models.CharField(max_length=50)
    team_name = models.CharField(max_length=50)
    conf_rank = models.IntegerField(null=True)
    div_rank = models.IntegerField(null=True)
    playoff_wins = models.IntegerField(null=True)
    playoff_losses = models.IntegerField(null=True)
    conf_count = models.IntegerField(null=True)
    div_count = models.IntegerField(null=True)
    # Nullable with a default because I'm not sure what kind of funky stuff nba has going on.
    # They probably have BAA/NBL seasons listed, and god help us if that's the case
    nba_finals_appearance = models.NullBooleanField(null=True, default=False)

    class Meta:
        db_table = 'team_season'
        unique_together = ("season", "season_type", "team", "per_mode")


class Injury(BaseModel):
    player = models.ForeignKey(Player)
    # This seems to always be "sidelined," but who knows.
    status = models.CharField(max_length=50, default="sidelined")
    # May be kind of tough to decipher the year, given Rotoworld's format
    injury_date = models.DateField(null=True)
    description = models.CharField(max_length=255, null=True)
    current_impact = models.CharField(max_length=255, null=True)
    report = models.TextField(null=True)

    class Meta:
        db_table = 'injury'


class Game(UserExposedModel):
    game_id = models.IntegerField()
    game_date_est = models.DateField()
    game_sequence = models.IntegerField()
    game_status_id = models.IntegerField()
    game_status_text = models.CharField(max_length=50)
    gamecode = models.CharField(max_length=100)
    home_team = models.ForeignKey(Team, related_name='home_team', null=True)
    visitor_team = models.ForeignKey(Team, related_name='visitor_team', null=True)
    season = models.ForeignKey(LeagueSeason, null=True)
    season_type = models.CharField(max_length=50, null=True)
    live_period = models.IntegerField()
    live_pc_time = models.CharField(max_length=100, null=True, default='')
    natl_tv_broadcaster_abbreviation = models.CharField(max_length=100, null=True, default='')
    live_period_time_bcast = models.CharField(max_length=100, null=True, default='')
    # Not entirely sure what the hell this field is/does
    wh_status = models.IntegerField(default=0)
    attendance = models.IntegerField(null=True)
    game_time = models.DurationField(null=True)

    # Recently added
    home_tv_broadcaster_abbreviation = models.CharField(max_length=25, null=True)
    away_tv_broadcaster_abbreviation = models.CharField(max_length=25, null=True)

    class Meta:
        db_table = 'game'

    def __str__(self):
        # TODO: Maybe add the score
        return "{date}: {visitor} @ {home}".format(date=self.game_date_est,
                                                   visitor=self.visitor_team,
                                                   home=self.home_team)


# This table may be superfluous...think about it before seeding them
class LineScore(BaseModel):
    game = models.ForeignKey(Game)
    game_date_est = models.DateField(null=True)
    game_sequence = models.IntegerField(default=0)
    team = models.ForeignKey(Team, null=True)
    # These fields are redundant but nba.com has them...hmm.
    team_abbreviation = models.CharField(max_length=5)
    team_city_name = models.CharField(max_length=50)
    team_nickname = models.CharField(max_length=50)
    # max_length = 5 bc XX-XX
    team_wins_losses = models.CharField(max_length=5)
    # This is also poor design...should really have a period model
    # or something and link them to the appropriate game
    pts_qtr1 = models.IntegerField(default=0, null=True)
    pts_qtr2 = models.IntegerField(default=0, null=True)
    pts_qtr3 = models.IntegerField(default=0, null=True)
    pts_qtr4 = models.IntegerField(default=0, null=True)
    pts_ot1 = models.IntegerField(default=0, null=True)
    pts_ot2 = models.IntegerField(default=0, null=True)
    pts_ot3 = models.IntegerField(default=0, null=True)
    pts_ot4 = models.IntegerField(default=0, null=True)
    pts_ot5 = models.IntegerField(default=0, null=True)
    pts_ot6 = models.IntegerField(default=0, null=True)
    pts_ot7 = models.IntegerField(default=0, null=True)
    pts_ot8 = models.IntegerField(default=0, null=True)
    pts_ot9 = models.IntegerField(default=0, null=True)
    pts_ot10 = models.IntegerField(default=0, null=True)
    pts = models.IntegerField(default=0, null=True)

    def __str__(self):
        return "{game};{team};{record};{points}".format(game=self.game, team=self.team, record=self.team_wins_losses,
                                                        points=self.pts)

    class Meta:
        db_table = 'line_score'


class GameOtherStats(BaseModel):
    game = models.ForeignKey(Game)
    team = models.ForeignKey(Team)
    team_abbreviation = models.CharField(max_length=5)
    team_city = models.CharField(max_length=50)
    pts_paint = models.IntegerField(null=True)
    pts_second_chance = models.IntegerField(null=True)
    pts_fb = models.IntegerField(null=True)
    largest_lead = models.IntegerField(null=True)
    lead_changes = models.IntegerField(null=True)
    times_tied = models.IntegerField(null=True)
    team_turnovers = models.IntegerField(null=True)
    total_turnovers = models.IntegerField(null=True)
    team_rebounds = models.IntegerField(null=True)
    pts_off_to = models.IntegerField(null=True)

    def __str__(self):
        return "<GameOtherStats>: {gm};{tm}".format(gm=str(self.game),
                                                    tm=str(self.team))

    class Meta:
        unique_together = ('game', 'team')
        db_table = 'game_other_stats'


class GameOfficialXref(BaseModel):
    official = models.ForeignKey(Official)
    game = models.ForeignKey(Game)

    def __str__(self):
        return "<GameOfficialXref>: {gm}; {ofc}".format(gm=str(self.game),
                                                        ofc=str(self.official))

    class Meta:
        unique_together = ('official', 'game')
        db_table = 'game_official_xref'


class TeamBoxScore(BaseModel):
    game = models.ForeignKey(Game)
    team = models.ForeignKey(Team, null=True)
    team_name = models.CharField(max_length=50)
    team_abbreviation = models.CharField(max_length=5)
    team_city = models.CharField(max_length=50)

    matchup = models.CharField(max_length=10, null=True)
    win_flag = models.NullBooleanField(null=True)

    class Meta:
        abstract = True


class PlayerBoxScore(BaseModel):
    game = models.ForeignKey(Game)
    player = models.ForeignKey(Player, null=True)
    team = models.ForeignKey(Team, null=True)
    team_abbreviation = models.CharField(max_length=5)
    team_city = models.CharField(max_length=50)
    player_name = models.CharField(max_length=201)
    start_position = models.CharField(max_length=20)
    comment = models.TextField(null=True)

    matchup = models.CharField(max_length=10, null=True)
    win_flag = models.NullBooleanField(null=True)

    class Meta:
        abstract = True


class TraditionalBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    fgm = models.IntegerField(default=0, null=True)
    fga = models.IntegerField(default=0, null=True)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    fg3m = models.IntegerField(default=0, null=True)
    fg3a = models.IntegerField(default=0, null=True)
    fg3_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ftm = models.IntegerField(default=0, null=True)
    fta = models.IntegerField(default=0, null=True)
    ft_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    oreb = models.IntegerField(default=0, null=True)
    dreb = models.IntegerField(default=0, null=True)
    reb = models.IntegerField(default=0, null=True)
    ast = models.IntegerField(default=0, null=True)
    stl = models.IntegerField(default=0, null=True)
    blk = models.IntegerField(default=0, null=True)
    tov = models.IntegerField(default=0, null=True)
    pf = models.IntegerField(default=0, null=True)
    pts = models.IntegerField(default=0, null=True)
    plus_minus = models.IntegerField(default=0, null=True)

    class Meta:
        abstract = True


class AdvancedBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1)
    off_rating = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    def_rating = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    net_rating = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ast_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ast_tov = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ast_ratio = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    dreb_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    reb_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    efg_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ts_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    usg_pct = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    pace = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    pie = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)

    class Meta:
        abstract = True


class MiscBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    pts_off_tov = models.IntegerField(default=0, null=True)
    pts_second_chance = models.IntegerField(default=0, null=True)
    pts_fb = models.IntegerField(default=0, null=True)
    pts_paint = models.IntegerField(default=0, null=True)
    opp_pts_off_tov = models.IntegerField(default=0, null=True)
    opp_pts_second_chance = models.IntegerField(default=0, null=True)
    opp_pts_fb = models.IntegerField(default=0, null=True)
    opp_pts_paint = models.IntegerField(default=0, null=True)
    blk = models.IntegerField(default=0, null=True)
    blka = models.IntegerField(default=0, null=True)
    pf = models.IntegerField(default=0, null=True)
    pfd = models.IntegerField(default=0, null=True)

    class Meta:
        abstract = True


class ScoringBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    pct_fga_2pt = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fga_3pt = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_2pt = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_2pt_midrange = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_3pt = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_fb = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_ft = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_off_tov = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts_paint = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_ast_2pm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_uast_2pm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_ast_3pm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_uast_3pm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_ast_fgm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_uast_fgm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        abstract = True


class UsageBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    usg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fgm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fga = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fg3m = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fg3a = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_ftm = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_fta = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_oreb = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_dreb = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_reb = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_ast = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_tov = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_stl = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_blk = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_blka = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pf = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pfd = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    pct_pts = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        abstract = True


class TrackingBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    distance = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    speed = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    touches = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    passes = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    ast = models.IntegerField(default=0, null=True)
    secondary_ast = models.IntegerField(default=0, null=True)
    ft_ast = models.IntegerField(default=0, null=True)
    dfgm = models.IntegerField(default=0, null=True)
    dfga = models.IntegerField(default=0, null=True)
    dfg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    oreb_chances = models.IntegerField(default=0, null=True)
    dreb_chances = models.IntegerField(default=0, null=True)
    reb_chances = models.IntegerField(default=0, null=True)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    contested_fgm = models.IntegerField(default=0, null=True)
    contested_fga = models.IntegerField(default=0, null=True)
    contested_fgpct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    uncontested_fgm = models.IntegerField(default=0, null=True)
    uncontested_fga = models.IntegerField(default=0, null=True)
    uncontested_fgpct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        abstract = True


class FourFactorsBoxScore(models.Model):
    min = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        abstract = True


class HustleStatsBoxScore(models.Model):
    minutes = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    contested_shots = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    contested_shots_2pt = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    contested_shots_3pt = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    deflections = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    loose_balls_recovered = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    charges_drawn = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    screen_assists = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)
    pts = models.DecimalField(max_digits=10, decimal_places=1, default=0, null=True)

    class Meta:
        abstract = True


class TeamTraditionalBoxScore(TeamBoxScore, TraditionalBoxScore):
    class Meta:
        db_table = 'team_traditional_box_score'


class PlayerTraditionalBoxScore(PlayerBoxScore, TraditionalBoxScore):
    class Meta:
        db_table = 'player_traditional_box_score'


class TeamAdvancedBoxScore(TeamBoxScore, AdvancedBoxScore):
    class Meta:
        db_table = 'team_advanced_box_score'


class PlayerAdvancedBoxScore(PlayerBoxScore, AdvancedBoxScore):
    class Meta:
        db_table = 'player_advanced_box_score'


class TeamMiscBoxScore(TeamBoxScore, MiscBoxScore):
    class Meta:
        db_table = 'team_misc_box_score'


class PlayerMiscBoxScore(PlayerBoxScore, MiscBoxScore):
    class Meta:
        db_table = 'player_misc_box_score'


class TeamScoringBoxScore(TeamBoxScore, ScoringBoxScore):
    class Meta:
        db_table = 'team_scoring_box_score'


class PlayerScoringBoxScore(PlayerBoxScore, ScoringBoxScore):
    class Meta:
        db_table = 'player_scoring_box_score'


class TeamUsageBoxScore(TeamBoxScore, UsageBoxScore):
    class Meta:
        db_table = 'team_usage_box_score'


class PlayerUsageBoxScore(PlayerBoxScore, UsageBoxScore):
    class Meta:
        db_table = 'player_usage_box_score'


class PlayerTrackingBoxScore(PlayerBoxScore, TrackingBoxScore):
    class Meta:
        db_table = 'player_tracking_box_score'


class TeamTrackingBoxScore(TeamBoxScore, TrackingBoxScore):
    class Meta:
        db_table = 'team_tracking_box_score'


class PlayerFourFactorsBoxScore(PlayerBoxScore, FourFactorsBoxScore):
    class Meta:
        db_table = 'player_four_factors_box_score'


class TeamFourFactorsBoxScore(TeamBoxScore, FourFactorsBoxScore):
    class Meta:
        db_table = 'team_four_factors_box_score'


class PlayerHustleStatsBoxScore(PlayerBoxScore, HustleStatsBoxScore):
    class Meta:
        db_table = 'player_hustle_stats_box_score'


class TeamHustleStatsBoxScore(TeamBoxScore, HustleStatsBoxScore):
    class Meta:
        db_table = 'team_hustle_stats_box_score'


class PlayByPlayEvent(BaseModel):
    # PBP events will be distinct by game and eventnum
    game = models.ForeignKey(Game)
    eventnum = models.IntegerField(default=0, null=True)
    eventmsgtype = models.IntegerField(null=True)
    eventmsgactiontype = models.IntegerField(null=True)
    period = models.IntegerField(default=1, null=True)
    wctimestring = models.CharField(max_length=100, null=True)
    pctimestring = models.CharField(max_length=100, null=True)
    homedescription = models.CharField(max_length=1000, null=True)
    neutraldescription = models.CharField(max_length=1000, null=True)
    visitordescription = models.CharField(max_length=1000, null=True)
    # This should be max_lenght=7, but the NBA likes to randomly include spaces...
    score = models.CharField(max_length=75, null=True)
    scoremargin = models.IntegerField(default=0, null=True)

    # Very poor design, but alas...
    person1type = models.IntegerField(null=True)
    player1 = models.ForeignKey(Player, related_name='player1', null=True, db_constraint=False)
    player1_name = models.CharField(max_length=201, null=True)
    player1_team = models.ForeignKey(Team, related_name='player1_team', null=True)
    player1_team_city = models.CharField(max_length=50, null=True)
    player1_team_nickname = models.CharField(max_length=50, null=True)
    player1_team_abbreviation = models.CharField(max_length=5, null=True)

    person2type = models.IntegerField(null=True)
    player2 = models.ForeignKey(Player, related_name='player2', null=True, db_constraint=False)
    player2_name = models.CharField(max_length=201, null=True)
    player2_team = models.ForeignKey(Team, related_name='player2_team', null=True)
    player2_team_city = models.CharField(max_length=50, null=True)
    player2_team_nickname = models.CharField(max_length=50, null=True)
    player2_team_abbreviation = models.CharField(max_length=5, null=True)

    person3type = models.IntegerField(null=True)
    player3 = models.ForeignKey(Player, related_name='player3', null=True, db_constraint=False)
    player3_name = models.CharField(max_length=201, null=True)
    player3_team = models.ForeignKey(Team, related_name='player3_team', null=True)
    player3_team_city = models.CharField(max_length=50, null=True)
    player3_team_nickname = models.CharField(max_length=50, null=True)
    player3_team_abbreviation = models.CharField(max_length=5, null=True)

    class Meta:
        db_table = 'play_by_play_event'

    def __str__(self):
        return ("{game}\nEventNum:{eventnum}\n{wctime}"
                " {period} {score}\n{home}\n{neutral}\n{visitor}").format(game=self.game, eventnum=self.eventnum,
                                                                          wctime=self.wctimestring, period=self.period,
                                                                          score=self.score,
                                                                          home=self.homedescription,
                                                                          neutral=self.neutraldescription,
                                                                          visitor=self.visitordescription)


class PlayerShotChartDetail(BaseModel):
    grid_type = models.CharField(max_length=100, default="")
    # This is only temporary because we haven't seeded all games. eventually this will be req'd
    game = models.ForeignKey(Game, null=True)
    game_event_id = models.IntegerField(default=0)
    player = models.ForeignKey(Player)
    team = models.ForeignKey(Team)
    # Including this field because team names can change...
    team_name = models.CharField(max_length=100)
    period = models.IntegerField(default=0)
    minutes_remaining = models.IntegerField(default=0)
    seconds_remaining = models.IntegerField(default=0)
    event_type = models.CharField(max_length=255, default="")
    action_type = models.CharField(max_length=255, default="")
    # Make these choice fields?
    shot_type = models.CharField(max_length=60, default="")
    shot_zone_basic = models.CharField(max_length=60, default="")
    shot_zone_area = models.CharField(max_length=60, default="")
    shot_zone_range = models.CharField(max_length=60, default="")
    shot_distance = models.IntegerField(default=0)
    loc_x = models.IntegerField(default=0)
    loc_y = models.IntegerField(default=0)
    # Dont know how this could ever be false...
    shot_attempted_flag = models.BooleanField(default=True)
    shot_made_flag = models.BooleanField(default=False)
    game_date = models.CharField(max_length=10)
    htm = models.CharField(max_length=10, default="")
    vtm = models.CharField(max_length=10, default="")

    class Meta:
        db_table = 'player_shot_chart_detail'
        unique_together = ("player", "game", "game_event_id")

    def __str__(self):
        return ";".join([str(self.game), str(self.player), self.shot_type,
                         str(self.shot_distance), str(self.shot_made_flag)])


class BaseSplit(BaseModel):
    season = models.ForeignKey(LeagueSeason, null=True)
    season_type = models.CharField(max_length=50)
    measure_type = models.CharField(max_length=50, default="")
    per_mode = models.CharField(max_length=50)
    group_set = models.CharField(max_length=100)
    group_value = models.CharField(max_length=100)
    # These next five fields should only be null for Shooting splits.
    gp = models.IntegerField(null=True)
    w = models.IntegerField(null=True)
    l = models.IntegerField(null=True)
    w_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    min = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        abstract = True


# The player and team split models exist primarily so coherent, correct unique_together constraints
# Can be created for both
class PlayerSplit(BaseSplit):
    player = models.ForeignKey(Player)
    # TODO: Why is there not a field for team? There has to be a reason

    class Meta:
        abstract = True

        unique_together = ('player', 'season', 'season_type',
                           'per_mode', 'group_set', 'group_value')


class TeamSplit(BaseSplit):
    team = models.ForeignKey(Team)

    class Meta:
        abstract = True

        unique_together = ('team', 'season', 'season_type',
                           'per_mode', 'group_set', 'group_value')


class TraditionalSplit(models.Model):
    fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fga = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    fg3m = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg3a = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fg3_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    ftm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fta = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ft_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    oreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    reb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ast = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    stl = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    blk = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    blka = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    tov = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pf = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pfd = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pts = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    plus_minus = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)

    class Meta:
        abstract = True


class PlayerTraditionalSplit(PlayerSplit, TraditionalSplit):
    dd2 = models.IntegerField(default=0, null=True)
    td3 = models.IntegerField(default=0, null=True)

    class Meta:
        db_table = 'player_traditional_splits'
        unique_together = PlayerSplit._meta.unique_together


class TeamTraditionalSplit(TeamSplit, TraditionalSplit):

    class Meta:
        db_table = 'team_traditional_split'
        unique_together = TeamSplit._meta.unique_together


class AdvancedSplit(models.Model):
    off_rating = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    def_rating = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    net_rating = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ast_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    ast_to = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    ast_ratio = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    dreb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    reb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    ts_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    usg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    pace = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    pie = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    uPER = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    aPER = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    per = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        abstract = True


class PlayerAdvancedSplit(PlayerSplit, AdvancedSplit):
    # These were added by nba.com very recently...
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    fga_pg = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    fgm_pg = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    fga = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)

    class Meta:
        db_table = 'player_advanced_split'
        unique_together = PlayerSplit._meta.unique_together


class TeamAdvancedSplit(TeamSplit, AdvancedSplit):

    class Meta:
        db_table = 'team_advanced_split'
        unique_together = TeamSplit._meta.unique_together


class ShootingSplit(models.Model):
    shot_split_type = models.CharField(max_length=100)
    shot_distance_group = models.CharField(max_length=100)
    fgm = models.DecimalField(max_digits=10, decimal_places=1)
    fga = models.DecimalField(max_digits=10, decimal_places=1)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3)
    fg3m = models.DecimalField(max_digits=10, decimal_places=1)
    fg3a = models.DecimalField(max_digits=10, decimal_places=1)
    fg3_pct = models.DecimalField(max_digits=10, decimal_places=3)
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3)
    blka = models.DecimalField(max_digits=10, decimal_places=1)
    pct_ast_2pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_2pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast_3pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_3pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast_fgm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_fgm = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        abstract = True


class PlayerShootingSplit(PlayerSplit, ShootingSplit):

    class Meta:
        db_table = 'player_shooting_split'
        unique_together = PlayerSplit._meta.unique_together

    def __str__(self):
        return ";".join([str(self.player), str(self.season),
                         self.season_type, self.per_mode, self.shot_split_type,
                        self.shot_distance_group])


class TeamShootingSplit(TeamSplit, ShootingSplit):

    class Meta:
        db_table = 'team_shooting_split'
        unique_together = TeamSplit._meta.unique_together


class MiscSplit(models.Model):
    pts_off_tov = models.DecimalField(max_digits=10, decimal_places=1)
    pts_second_chance = models.DecimalField(max_digits=10, decimal_places=1)
    pts_fb = models.DecimalField(max_digits=10, decimal_places=1)
    opp_pts_off_tov = models.DecimalField(max_digits=10, decimal_places=1)
    opp_pts_second_chance = models.DecimalField(max_digits=10, decimal_places=1)
    opp_pts_fb = models.DecimalField(max_digits=10, decimal_places=1)
    opp_pts_paint = models.DecimalField(max_digits=10, decimal_places=1)
    pts_paint = models.DecimalField(max_digits=10, decimal_places=1)

    class Meta:
        abstract = True


class PlayerMiscSplit(PlayerSplit, MiscSplit):

    class Meta:
        db_table = 'player_misc_split'
        unique_together = PlayerSplit._meta.unique_together


class TeamMiscSplit(TeamSplit, MiscSplit):

    class Meta:
        db_table = 'team_misc_split'
        unique_together = TeamSplit._meta.unique_together


class UsageSplit(models.Model):
    usg_pct = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fgm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fga = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fg3m = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fg3a = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ftm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fta = models.DecimalField(max_digits=10, decimal_places=3)
    pct_oreb = models.DecimalField(max_digits=10, decimal_places=3)
    pct_dreb = models.DecimalField(max_digits=10, decimal_places=3)
    pct_reb = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast = models.DecimalField(max_digits=10, decimal_places=3)
    pct_tov = models.DecimalField(max_digits=10, decimal_places=3)
    pct_stl = models.DecimalField(max_digits=10, decimal_places=3)
    pct_blka = models.DecimalField(max_digits=10, decimal_places=3)
    pct_blk = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pf = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pfd = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        abstract = True


class PlayerUsageSplit(PlayerSplit, UsageSplit):

    class Meta:
        db_table = 'player_usage_split'
        unique_together = PlayerSplit._meta.unique_together


class ScoringSplit(models.Model):
    pct_fga_2pt = models.DecimalField(max_digits=10, decimal_places=3)
    pct_fga_3pt = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_2pt = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_2pt_midrange = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_3pt = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_fb = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_ft = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_off_tov = models.DecimalField(max_digits=10, decimal_places=3)
    pct_pts_paint = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast_2pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_2pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast_3pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_3pm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_ast_fgm = models.DecimalField(max_digits=10, decimal_places=3)
    pct_uast_fgm = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        abstract = True


class PlayerScoringSplit(PlayerSplit, ScoringSplit):

    class Meta:
        db_table = 'player_scoring_split'
        unique_together = PlayerSplit._meta.unique_together


class TeamScoringSplit(TeamSplit, ScoringSplit):

    class Meta:
        db_table = 'team_scoring_split'
        unique_together = TeamSplit._meta.unique_together


class FourFactorsSplit(models.Model):
    efg_pct = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    fta_rate = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    opp_efg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    opp_fta_rate = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    opp_oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)

    class Meta:
        abstract = True


class TeamFourFactorsSplit(TeamSplit, FourFactorsSplit):

    class Meta:
        db_table = 'team_four_factors_split'
        unique_together = TeamSplit._meta.unique_together


class OpponentSplit(models.Model):
    opp_fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fga = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_fg3m = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg3a = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg3_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_ftm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fta = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_ft_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_oreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_reb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_stl = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_blk = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_blka = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_tov = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pf = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pfd = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    plus_minus = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)

    class Meta:
        abstract = True


class TeamOpponentSplit(TeamSplit, OpponentSplit):

    class Meta:
        db_table = 'team_opponent_split'
        unique_together = TeamSplit._meta.unique_together


class DefenseSplit(models.Model):
    def_rating = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_pct = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    stl = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    blk = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_off_tov = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_2nd_chance = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_fb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_paint = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        abstract = True


class TeamDefenseSplit(TeamSplit, DefenseSplit):
    def_rating = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    stl = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    blk = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_off_tov = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_2nd_chance = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_fb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    opp_pts_paint = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        db_table = 'team_defense_split'
        unique_together = TeamSplit._meta.unique_together


class Lineup(BaseModel):
    unique_together = ('season', 'season_type', 'measure_type',
                       'per_mode', 'team', 'group_quantity')
    season = models.ForeignKey(LeagueSeason, null=True)
    season_type = models.CharField(max_length=50)
    measure_type = models.CharField(max_length=50, default="")
    per_mode = models.CharField(max_length=50)
    players = models.ManyToManyField(Player)
    team = models.ForeignKey(Team)
    team_abbreviation = models.CharField(max_length=5)
    gp = models.IntegerField(null=True)
    w = models.IntegerField(null=True)
    l = models.IntegerField(null=True)
    w_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    min = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    group_quantity = models.IntegerField(null=True)

    @classmethod
    def filter_on_players(cls, players, filter_dict=None):
        if filter_dict is None:
            filter_dict = {}
        elif "player" in filter_dict or "players" in filter_dict:
            raise ValueError("Don't pass the player(s) you want to filter on "
                             "in filter_dict.")
        if isinstance(players, QuerySet):
            players = list(players.values_list('id', flat=True).distinct())
        elif not isinstance(players, list):
            raise ValueError("You must pass a QuerySet or list to this function."
                             " You passed a {t}".format(t=type(players)))
        num_players = len(players)
        lineup_query = cls.objects.annotate(count=Count('players')).filter(count=num_players)
        lineup_query = lineup_query.filter(**filter_dict)

        for player in players:
            lineup_query = lineup_query.filter(players__id=player)

        return lineup_query

    def __str__(self):
        return "-".join(map(str, [self.season, self.season_type,
                                  self.measure_type, self.per_mode,
                                  self.players.all(), self.team_abbreviation]))

    class Meta:
        abstract = True


class BaseLineup(Lineup, TraditionalSplit):

    class Meta:
        db_table = 'base_lineup'


class AdvancedLineup(Lineup, AdvancedSplit):

    class Meta:
        db_table = 'advanced_lineup'


class MiscLineup(Lineup, MiscSplit):

    class Meta:
        db_table = 'misc_lineup'


class FourFactorsLineup(Lineup):
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        db_table = 'four_factors_lineup'


class ScoringLineup(Lineup, ScoringSplit):

    class Meta:
        db_table = 'scoring_lineup'


class OpponentLineup(Lineup, OpponentSplit):

    class Meta:
        db_table = 'opponent_lineup'


class UsageLineup(Lineup, UsageSplit):

    class Meta:
        db_table = 'usage_lineup'


class PlayerOnOff(BaseModel):
    # None of these are actually nullable, South is stupid and wont let you add
    # Non-nullable fields without a default. These were added before any instances were
    # Actually created. <eyeroll>
    season = models.ForeignKey(LeagueSeason, null=True)
    season_type = models.CharField(max_length=50, null=True)
    measure_type = models.CharField(max_length=50, null=True)
    per_mode = models.CharField(max_length=50, null=True)
    team = models.ForeignKey(Team)
    team_abbreviation = models.CharField(max_length=10, null=True)
    player = models.ForeignKey(Player)
    court_status = models.CharField(max_length=10)
    gp = models.IntegerField()
    min = models.DecimalField(max_digits=10, decimal_places=1)

    class Meta:
        abstract = True
        unique_together = ('season', 'season_type', 'measure_type',
                           'per_mode', 'team', 'player', 'court_status')


class PlayerOnOffSummary(PlayerOnOff):
    plus_minus = models.DecimalField(max_digits=10, decimal_places=1)
    off_rating = models.DecimalField(max_digits=10, decimal_places=1)
    def_rating = models.DecimalField(max_digits=10, decimal_places=1)
    net_rating = models.DecimalField(max_digits=10, decimal_places=1)

    class Meta:
        db_table = 'player_on_off_summary'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerBaseOnOffDetail(PlayerOnOff, TraditionalSplit):

    class Meta:
        db_table = 'player_base_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerAdvancedOnOffDetail(PlayerOnOff, AdvancedSplit):

    class Meta:
        db_table = 'player_advanced_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerMiscOnOffDetail(PlayerOnOff, MiscSplit):

    class Meta:
        db_table = 'player_misc_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerFourFactorsOnOffDetail(PlayerOnOff):
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    tm_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_efg_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_fta_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)
    opp_oreb_pct = models.DecimalField(max_digits=10, decimal_places=3, default=0, null=True)

    class Meta:
        db_table = 'player_four_factors_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerScoringOnOffDetail(PlayerOnOff, ScoringSplit):

    class Meta:
        db_table = 'player_scoring_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerOpponentOnOffDetail(PlayerOnOff):
    opp_fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fga = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_fg3m = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg3a = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fg3_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_ftm = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_fta = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_ft_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True, default=0)
    opp_oreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_reb = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_stl = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_blk = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_blka = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_tov = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pf = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pfd = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    opp_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)
    plus_minus = models.DecimalField(max_digits=10, decimal_places=1, null=True, default=0)

    class Meta:
        db_table = 'player_opponent_on_off_detail'
        unique_together = PlayerOnOff._meta.unique_together


class PlayerGameLog(BaseModel):
    player = models.ForeignKey(Player)
    # Should never actually be null
    team = models.ForeignKey(Team, null=True)
    game = models.ForeignKey(Game)
    season = models.ForeignKey(LeagueSeason, null=True)
    game_date = models.DateField()
    matchup = models.CharField(max_length=30)
    win_flag = models.BooleanField()

    def __str__(self):
        return ";".join(map(str, [self.player.display_first_last,
                                  self.team.abbreviation,
                                  self.game_date,
                                  self.matchup,
                                  self.win_flag]))

    class Meta:
        db_table = 'player_game_log'
        unique_together = (('player', 'game'),
                           ('player', 'game_date'))


class PlayerTracking(BaseModel):
    player = models.ForeignKey(Player)

    season = models.ForeignKey(LeagueSeason, null=True)
    season_type = models.CharField(max_length=50)
    pt_measure_type = models.CharField(max_length=50, default="")
    per_mode = models.CharField(max_length=50)
    group_set = models.CharField(max_length=100)
    group_value = models.CharField(max_length=100)
    gp = models.IntegerField(null=True)
    w = models.IntegerField(null=True)
    l = models.IntegerField(null=True)
    min = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        abstract = True
        unique_together = ('player', 'season', 'season_type',
                           'pt_measure_type', 'per_mode', 'group_set',
                           'group_value')


class PlayerSpeedDistanceTracking(PlayerTracking):
    dist_feet = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dist_miles = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dist_miles_off = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dist_miles_def = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    avg_speed = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    avg_speed_off = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    avg_speed_def = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        db_table = 'player_speed_distance_tracking'
        unique_together = PlayerTracking._meta.unique_together


class PlayerReboundingTracking(PlayerTracking):
    oreb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    oreb_contest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    oreb_uncontest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    oreb_contest_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    oreb_chances = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    oreb_chance_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    oreb_chance_defer = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    oreb_chance_pct_adj = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    avg_oreb_dist = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_contest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_uncontest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_contest_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    dreb_chances = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_chance_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    dreb_chance_defer = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb_chance_pct_adj = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    avg_dreb_dist = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb_contest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb_uncontest = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb_contest_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    reb_chances = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb_chance_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    reb_chance_defer = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    reb_chance_pct_adj = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    avg_reb_dist = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        db_table = 'player_rebounding_tracking'
        unique_together = PlayerTracking._meta.unique_together


class PlayerPossessionsTracking(PlayerTracking):
    points = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    front_ct_touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    time_of_poss = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    avg_sec_per_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    avg_drib_per_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    pts_per_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    elbow_touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    post_touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    paint_touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    pts_per_elbow_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    pts_per_post_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    pts_per_paint_touch = models.DecimalField(max_digits=10, decimal_places=1, null=True)

    class Meta:
        db_table = 'player_possessions_tracking'
        unique_together = PlayerTracking._meta.unique_together


class PlayerShotTypeTracking(PlayerTracking):
    shot_type = models.CharField(max_length=30)
    fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    fga = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    fg3m = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    fg3a = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    fg3_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    efg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)

    class Meta:
        db_table = 'player_shot_type_tracking'
        unique_together = ('player', 'season', 'season_type',
                           'pt_measure_type', 'per_mode', 'group_set',
                           'group_value', 'shot_type')


class PlayerDefenseTracking(PlayerTracking):
    stl = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    blk = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    dreb = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    def_rim_fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    def_rim_fga = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    def_rim_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)

    class Meta:
        db_table = 'player_defense_tracking'
        unique_together = PlayerTracking._meta.unique_together


class PlayerPassingTracking(PlayerTracking):
    ast = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    ft_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    secondary_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    potential_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    ast_pts_created = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    ast_adj = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    ast_to_pass_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    ast_to_pass_pct_adj = models.DecimalField(max_digits=10, decimal_places=3, null=True)

    class Meta:
        db_table = 'player_passing_tracking'
        unique_together = PlayerTracking._meta.unique_together


class PlayerEfficiencyTracking(PlayerTracking):
    points = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    drive_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    drive_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    catch_shoot_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    catch_shoot_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    pull_up_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    pull_up_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    paint_touch_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    paint_touch_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    post_touch_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    post_touch_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    elbow_touch_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    elbow_touch_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    eff_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)


class PlayerTouchTracking(PlayerTracking):
    touch_type = models.CharField(max_length=50)
    touches = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_fgm = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_fga = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_fg_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_ftm = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_fta = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_ft_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_pts = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_pts_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_passes = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_passes_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_ast = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_ast_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_tov = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_tov_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    touch_fouls = models.DecimalField(max_digits=10, decimal_places=1, null=True)
    touch_fouls_pct = models.DecimalField(max_digits=10, decimal_places=3, null=True)

    class Meta:
        db_table = 'player_touch_tracking'
        unique_together = ('player', 'season', 'season_type',
                           'pt_measure_type', 'per_mode', 'group_set',
                           'group_value', 'touch_type')
