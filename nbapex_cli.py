import click
import logging
import django; django.setup()
from nba_py.player import PlayerList
from nba_stats.web_handlers.player_handler import PlayerHandler
from nba_stats.models import Player
log = logging.getLogger('stats')


class CliConfig:
    def __init__(self, database='default'):
        self.database = database


@click.group()
@click.option("--database", default="default", help="Which database to use from your django settings.")
@click.pass_context
def cli(ctx, database):
    ctx.obj = CliConfig(database=database)


@cli.command()
@click.option("--active-only", is_flag=True)
@click.pass_obj
def init_players(cli_config, active_only=True):
    msg = f"Initializing players in Database: {cli_config.database}"
    click.echo(msg)
    log.info(msg)

    active_only = 1 if active_only else 0
    player_list = PlayerList(only_current=active_only)
    cur = 1
    total = len(player_list.info())
    players_to_create = []
    player_ids = player_list.info()['PERSON_ID']

    for player_id in player_ids:
        player_handler = PlayerHandler(player=int(player_id), database=cli_config.database)
        player_handler.fetch_raw_data()
        player_instance = player_handler.create_update_player()
        players_to_create.append(player_instance)

        progress_message = f"{cur}/{total} = {cur/total * 100}) + % done with players."
        log.info(progress_message)
        cur += 1

    Player.objects.using(cli_config.database).bulk_create(players_to_create)
    msg = "Finished seeding players."
    log.info(msg)

if __name__ == "__main__":
    cli()
