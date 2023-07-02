# Import WebClient from Python SDK (github.com/slackapi/python-slack-sdk)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from template_python.credentials import getpwd

class Slack_instance:

    def __init__(self):
        #GetSlack
        self.client = WebClient(token=getpwd('Slack-pythonbot', 'token'))
        return

    # Destructor
    def __del__(self):
        return

    def do_actions(self): 
        return 0

    def channel_id(self, channel_name:str) -> str:
        """Returns channel id for the specified channel name
        Args:
            channel_name (str): Name of the slack channel
        Returns:
            str: Channel ID
        """
        return getpwd('Slack-pythonbot', channel_name)

    def init_block(self):
        self.block = []
        return
    
    def msg(self, message:str, channel:str="python"):
        """Sends Slack message
        Args:
            message (str): Message to be sent
            channel (str, optional): Slack channel to send the message to. Defaults to "#python".
        """
        err = 0
        try:
            _ = self.client.chat_postMessage(
                channel=self.channel_id(channel),
                text=message)
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            print(f'NG - Slack message not sent: {str(e)}')
            err = 1
        return err
    
        
    def add_text(self, text, image_url=None,image_alt_text=""):
        """Adds markdown element to block message
        Args:
            text (str): Text to display
            image_url (str, optional): Image to display. Defaults to None.
            image_alt_text (str, optional): Alt string for image. Defaults to "".
        """ 
        if not image_url:
            self.block.append(
                {
                    "type": "section",
                    "text": { "type": "mrkdwn", "text": text}
                })
        else:
            self.block.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": text},
                    "accessory": {
                        "type": "image",
                        "image_url": image_url,
                        "alt_text": image_alt_text
                    }
                })
            
        return
    
    def add_divider(self):
        """Adds divider to the block message
        """
        self.block.append({"type": "divider"})
        return
    
    def post_block(self, channel):
        """Posts the currently constructed block to slack chat
        Args:
            channel (str): Channel name
        """
        err = 0
        try:
            response = self.client.chat_postMessage(channel=self.channel_id(channel),blocks=self.block)
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            print(f'NG - Slack message not sent: {str(e)}')
            err = 1
        return err