import datetime
import random

from discord import Message as Discord_Message

class Message(object):
    def __init__(self, bot,
                 message_id: int,
                 channel_id: int,
                 author_id: int,
                 content: str,
                 xp_multiplier: int,
                 *args, **kwargs):
        self.bot = bot
        self.message_id = message_id
        self.channel_id = channel_id
        self.author_id = author_id
        self.xp_multiplier = xp_multiplier
        self.content = content

    async def post(self) -> None:
        query = """INSERT INTO messages ( message_id, channel_id, author_id, content)
                   VALUES ( $1, $2, $3, $4 )
                   ON CONFLICT DO NOTHING"""
        await self.bot.db.execute(query, self.message_id, self.channel_id, self.author_id,
                                  self.content)

    @classmethod
    async def on_message(cls, bot, message: Discord_Message, xp_multiplier:int) -> None:
        print(f"{message.author} : {message.content}")
        self = cls(bot=bot, content=message.content,
                   message_id=message.id, channel_id=message.channel.id, author_id=message.author.id, xp_multiplier=xp_multiplier)
        await self.post()
        if message.author.bot:
            return
        user = await bot.db.get_user(id=message.author.id)
        xp = random.randint(15, 25)
        now = datetime.datetime.now()
        difference = datetime.timedelta(seconds=0)
        if user.last_xp_added is not None:
            difference = now - user.last_xp_added
        if difference > datetime.timedelta(minutes=1) or user.last_xp_added is None:
            user.total_xp += (xp * self.xp_multiplier)
            user.last_xp_added = now
            await bot.db.execute('UPDATE users SET total_xp = $1, last_xp_added = $2 WHERE id = $3', user.total_xp, user.last_xp_added, user.id)
        await bot.db.execute('UPDATE users SET messages_sent = messages_sent + 1 WHERE id = $1', user.id)