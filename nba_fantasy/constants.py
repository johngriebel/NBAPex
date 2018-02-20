# There has to be a better way to do all this position garbage
ELIGIBILITY = {1: ['point_guard', 'guard', 'bench', 'utility'],
               2: ['shooting_guard', 'guard', 'wing', 'bench', 'utility'],
               3: ['small_forward', 'wing', 'forward', 'bench', 'utility'],
               4: ['power_forward', 'big', 'forward', 'bench', 'utility'],
               5: ['center', 'big', 'bench', 'utility']}

POINT_GUARD = "point_guard"
SHOOTING_GUARD = "shooting_guard"
SMALL_FORWARD = "small_forward"
POWER_FORWARD = "power_forward"
CENTER = "center"
GUARD = "guard"
FORWARD = "forward"
WING = "wing"
BIG = "big"
BENCH = "bench"
UTILITY = "util"
INJURED = "inj"
TOTAL = "total"

# I'm really starting to not like this at all
POSITION_ORDER = {POINT_GUARD: (1, "PG", [1]),
                  SHOOTING_GUARD: (2, "SG", [2]),
                  GUARD: (3, "G", [1, 2]),
                  SMALL_FORWARD: (4, "SF", [3]),
                  WING: (5, "WING", [2, 3]),
                  POWER_FORWARD: (6, "PF", [4]),
                  FORWARD: (7, "F", [3, 4]),
                  CENTER: (8, "C", [5]),
                  BIG: (9, "BIG", [4, 5]),
                  UTILITY: (10, "UTIL", [1, 2, 3, 4, 5]),
                  BENCH: (11, "BN", [1, 2, 3, 4, 5]),
                  INJURED: (12, "INJ", [1, 2, 3, 4, 5]),
                  TOTAL: (20, "TOT", [1, 2, 3, 4, 5])}

LINEUP_POSITIONS = ((POINT_GUARD, "PG"),
                    (SHOOTING_GUARD, "SG"),
                    (SMALL_FORWARD, "SF"),
                    (POWER_FORWARD, "PF"),
                    (CENTER, "C"),
                    (GUARD, "G"),
                    (FORWARD, "F"),
                    (WING, "W",),
                    (BIG, "B"),
                    (BENCH, "BN"),
                    (UTILITY, "UTIL"),
                    (INJURED, "INJ"))

# Django docs say it's best to define this here...
DAILY_INDIV_GAME = "DIG"
DAILY_ALL_GAME = "DAG"
WEEKLY = "WK"
LINEUP_CHANGE_CHOICES = ((DAILY_INDIV_GAME, "Daily, at start of individual game."),
                         (DAILY_ALL_GAME, "Daily, at beginning of all games."),
                         (WEEKLY, "Weekly, before the first game of the week."))

ROTISSERIE = "ROTO"
HEAD_TO_HEAD = "H2H"
SCHEDULE_TYPE_CHOICES = ((ROTISSERIE, "Rotisserie"),
                         (HEAD_TO_HEAD, "Head to head"))

SALARY_CAP = "SC"
SNAKE = "SK"
DRAFT_TYPE_CHOICES = ((SALARY_CAP, "Salary Cap"),
                      (SNAKE, "Snake Draft"))

CATEGORY = "CAT"
POINTS = "PTS"
SCORING_TYPE_CHOICES = ((CATEGORY, "Categories"),
                        (POINTS, "Points"))