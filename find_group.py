from neonize.client import NewClient
from neonize.events import ConnectedEv

client = NewClient("./auth.db")

@client.event(ConnectedEv)
def on_connected(client, _):
    groups = client.get_joined_groups()
    print(f"\n{'='*60}")
    print(f" Found {len(groups)} groups")
    print(f"{'='*60}\n")
    for g in groups:
        jid = f"{g.JID.User}@{g.JID.Server}"
        name = g.GroupName.Name if hasattr(g, "GroupName") else "N/A"
        print(f"  {name}")
        print(f"  JID: {jid}")
        print(f"  {'-'*56}")

client.connect()