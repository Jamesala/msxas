from disnake import Color, Embed
from disnake.ext.commands import Cog, slash_command

from core.match import start_queue
from core.embeds import error

class Match(Cog):
    """
    ⚔️;Mecze
    """

    def __init__(self, bot):
        self.bot = bot

    async def send_new_queues(self):
        await self.bot.wait_until_ready()
        channels = await self.bot.fetch("SELECT * FROM queuechannels")
        for data in channels:
            channel = self.bot.get_channel(data[0])
            if channel:
                try:
                    await channel.send(
                        embed=Embed(
                            title=":warning: OGŁOSZENIE",
                            description="Bot został zaktualizowany w celu konserwacji. Kolejki **przed** tą wiadomością są teraz nieprawidłowe. Skorzystaj z kolejki pod tą wiadomością. \n"
                                        ":D",
                            color=Color.yellow()
                        )
                    )
                    await start_queue(self.bot, channel, data[2])
                except:
                    import traceback
                    print(traceback.format_exc())

    @Cog.listener()
    async def on_ready(self):
        await self.send_new_queues()

    @slash_command(name="start")
    async def start_slash(self, ctx):
        """
        Uruchom kolejkę MIXÓW.
        """
        game_check = await self.bot.fetchrow(f"SELECT * FROM queuechannels WHERE channel_id = {ctx.channel.id}")
        if not game_check:
            return await ctx.send(embed=error("Ten kanał nie jest kanałem kolejki."))
        try:
            await ctx.send("Gra została rozpoczęta!")
        except:
            pass
        await start_queue(self.bot, ctx.channel, game_check[2], ctx.author)

def setup(bot):
    bot.add_cog(Match(bot))
