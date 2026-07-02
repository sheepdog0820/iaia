from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.notification_group = f"notifications_user_{user.pk}"
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        group = getattr(self, "notification_group", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def notification_created(self, event):
        await self.send_json(
            {
                "type": "notification.created",
                "notification": event["notification"],
                "unread_count": event["unread_count"],
            }
        )
