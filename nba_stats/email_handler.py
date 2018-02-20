from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from nba_stats.super_secret_passwords import GMAIL_ACCT, GMAIL_PASSWORD
# TODO: Would eventually like this class to be able to monitor a given task and
# send emails at given intervals in the task (e.g. 25% done, 50% done, etc.) as well as
# if the process hangs, i.e. nba.com stops responding.
# Automatic restart? Might be best for a diff module.


class EmailHandler:

    def __init__(self):
        self.msg = MIMEMultipart('alternative')
        self.sender = SMTP('smtp.gmail.com', 587)
        self.sender.ehlo()
        self.sender.starttls()
        self.sender.login(GMAIL_ACCT, GMAIL_PASSWORD)
        self.recipient = GMAIL_ACCT

    def send_email(self, message, subject="Message From NBAPex", attachment_path=None):
        self.msg['Subject'] = subject
        self.msg['From'] = GMAIL_ACCT
        content = MIMEText(message, 'plain')
        self.msg.attach(content)
        if attachment_path is not None:
            with open(attachment_path, "r") as attachment_file:
                attachment = MIMEText(attachment_file.read())
                attachment.add_header("Content-Disposition", "attachment", filename=attachment_path.split("/")[-1])
                self.msg.attach(attachment)
        failures = self.sender.sendmail(GMAIL_ACCT, self.recipient, self.msg.as_string())
        return failures
