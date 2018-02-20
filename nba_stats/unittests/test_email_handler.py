from nba_stats.email_handler import EmailHandler
from nose2.tools.decorators import with_setup

email_handler = None


def setup_func():
    global email_handler
    email_handler = EmailHandler()


def teardown_func():
    pass


@with_setup(setup_func)
def test_sending_email():
    resp = email_handler.send_email(message="Test Email")
    assert resp == {}
