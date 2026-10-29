from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv
from neonize.utils import extract_text

client = NewClient("./auth.db")

@client.event(ConnectedEv)
def on_connected(_, __):
    print("Connected to WhatsApp")

def start_listener(on_message):
    @client.event(MessageEv)
    def on_message_event(_, message: MessageEv):
        source = message.Info.MessageSource
        chat = source.Chat
        jid = f"{chat.User}@{chat.Server}"
        try:
            text = extract_text(message.Message)
        except Exception:
            text = message.Message.conversation or (
                message.Message.extendedTextMessage.text
                if message.Message.extendedTextMessage else ""
            )
        if not text:
            return
        msg_id = message.Info.ID
        is_group = bool(source.IsGroup)
        is_from_me = bool(source.IsFromMe)
        sender_jid = f"{source.Sender.User}@{source.Sender.Server}" if source.Sender else ""
        on_message(
            client=client,
            jid=jid,
            text=text,
            msg_id=msg_id,
            is_group=is_group,
            is_from_me=is_from_me,
            sender_jid=sender_jid
        )

    client.connect()
