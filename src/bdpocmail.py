import smtplib, ssl
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

class SendMail:
  def __init__(self, template_dir="/opt/bdpoc/emails", email = "pdmone@biendongpoc.vn", smtp_server = "smtp.office365.com", password = "bdpoc@2602", port=587):
    self.smtp_server = smtp_server 
    self.port = port
    self.password = password
    self.template_dir = template_dir
    self.email = email
    self._environment = None
  def getEnvironment(self):
    if self._environment is None:
      self._environment = Environment(loader=FileSystemLoader(self.template_dir))
    return self._environment
  def sendmail(self, to, subject, content):
    # Create a secure SSL context
    context = ssl.create_default_context()
    with smtplib.SMTP(self.smtp_server, self.port) as server:
      server.ehlo()  # Can be omitted
      server.starttls(context=context)
      server.ehlo()  # Can be omitted
      server.login(self.email, self.password)
      msg = MIMEText(content)
      msg["Subject"] = subject
      msg["From"] = self.email
      msg["To"] = ",".join(to) if type(to) == list else to
      server.sendmail(self.email, to, msg.as_string())
  def formatAndSend(self, to, templateName, **kwargs):
    subject_template = self.getEnvironment().get_template( f"{templateName}.subject.tpl" )
    subject = subject_template.render(**kwargs)

    content_template = self.getEnvironment().get_template( f"{templateName}.tpl" )
    content = content_template.render(**kwargs)
    self.sendmail(to, subject, content)
