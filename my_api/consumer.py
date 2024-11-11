import json

from channels.generic.websocket import AsyncWebsocketConsumer


class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("Connected 1")
        self.issue_id = self.scope["url_route"]["kwargs"]["issue_id"]
        self.room_group_name = f"comments_{self.issue_id}"
        print(f"ISSUE ID: {self.issue_id}")
        print(f"NAME: {self.room_group_name}")
        if self.channel_layer is not None:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            print("Connected")

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive(self, text_data):
        pass

    async def comment_message(self, event):
        await self.send(
            text_data=json.dumps({"type": "comment", "comment": event["comment"]})
        )
