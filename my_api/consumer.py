from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.issue_id = self.scope['url_route']['kwargs']['issue_id']
        self.room_group_name = f'comments_{self.issue_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass

    async def comment_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment',
            'comment': event['comment']
        }))