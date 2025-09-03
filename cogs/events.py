import os
import traceback
from io import StringIO
from core import embeds
from disnake import Color, Embed, File, Game
from disnake.ext import commands, tasks
from disnake.ext.commands import Cog
from dotenv import load_dotenv
from cogs.admin import leaderboard_persistent

load_dotenv()

BOT_ID = int(os.getenv("BOT_ID"))
ERROR_LOG_CHANNEL_ID_1 = int(os.getenv("ERROR_LOG_CHANNEL_ID_1"))
ERROR_LOG_CHANNEL_ID_2 = int(os.getenv("ERROR_LOG_CHANNEL_ID_2"))

class Events(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.persistent_lb.start()

    @tasks.loop(seconds=5)
    async def persistent_lb(self):
        await self.bot.wait_until_ready()
        entries = await self.bot.fetch("persistent_lb")
        for entry in entries:
            channel = self.bot.get_channel(entry["channel_id"])
            if not channel:
                continue
            try:
                msg = await channel.fetch_message(entry["msg_id"])
                if msg:
                    embed = await leaderboard_persistent(self.bot, channel, entry["game"])
                    await msg.edit(embed=embed)
            except:
                continue

    @Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.bot.execute("queuechannels", "DELETE", None, {"channel_id": channel.id})
        await self.bot.execute("winner_log_channel", "DELETE", None, {"channel_id": channel.id})
        await self.bot.execute("persistent_lb", "DELETE", None, {"channel_id": channel.id})

    @Cog.listener()
    async def on_message(self, msg):
        queue_channels = await self.bot.fetch("queuechannels")
        if not queue_channels:
            return

        channel_ids = [channel["channel_id"] for channel in queue_channels]
        if msg.channel.id in channel_ids:
            if not msg.embeds:
                try:
                    await msg.delete()
                except:
                    pass
                return

            embed = msg.embeds[0]
            title = embed.title if embed.title else ""
            description = embed.description if embed.description else ""

            valid_titles = [
                "Match Overview - SR Tournament Draft",
                "Match Overview - Valorant Competitive",
                "MIXY - Overwatch 2",
                "MECZ - Spectre Divide",
                "MIXY - Marvel Rivals",
                "Match Overview",
                "1v1 Test Mode",
                ":warning: OGŁOSZENIE"
            ]

            valid_descriptions = [
                "Znaleziono grę! Czas się przygotować!",
                "Wspomniani gracze zostali usunięci z kolejki za nieprzygotowanie się na czas.",
                "Nie udało się zalogować gry",
                "został pomyślnie ustawiony jako kanał kolejki."
            ]

            if title not in valid_titles and description not in valid_descriptions:
                try:
                    await msg.delete()
                except:
                    pass

    async def setup_collections(self):
        existing_collections = await self.bot.db.list_collection_names()
        for collection in self.bot.collections:
            if collection not in existing_collections:
                await self.bot.db.create_collection(collection)

    @Cog.listener()
    async def on_ready(self):
        print("*********\nBot is Ready.\n*********")
        await self.setup_collections()
        await self.bot.change_presence(activity=Game(name="MECZE 3V3"))

    @Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
            pass
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(embed=embeds.error(str(error)))
        else:
            await self.bot.wait_until_ready()
            channel_id = ERROR_LOG_CHANNEL_ID_1 if self.bot.user.id == BOT_ID else ERROR_LOG_CHANNEL_ID_2
            channel = self.bot.get_channel(channel_id)
            command = ctx.command if isinstance(ctx, commands.Context) else ctx.data.name

            e = Embed(
                title="Exception!",
                description=f"Guild: {ctx.guild.name}\nGuildID: {ctx.guild.id}\nUser: {ctx.author}\nUserID: {ctx.author.id}\n\nError: {error}\nCommand: {command}",
                color=Color.blurple(),
            )

            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = "".join(lines)

            await channel.send(
                embed=e,
                file=File(filename="traceback.txt", fp=StringIO(f"{traceback_text}\n")),
            )

    @Cog.listener()
    async def on_slash_command_error(self, ctx, error):
        await self.on_command_error(ctx, error)

    @Cog.listener('on_message')
    async def process_mvp_votes(self, msg):
        if msg.author.bot or msg.guild:
            return

        votes = await self.bot.fetch("mvp_voting", {"user_id": msg.author.id})
        for vote in votes:
            if msg.content.isnumeric():
                if int(msg.content) > 10:
                    return await msg.channel.send(embed=embeds.error("Głosować może tylko 12 osób."))

                members = await self.bot.fetch("members_history", {"game_id": vote["game_id"]})
                for i, member in enumerate(members):
                    if i + 1 == int(msg.content):
                        if member["user_id"] == msg.author.id:
                            return await msg.channel.send(embed=embeds.error("Nie możesz głosować na siebie ;-;"))

                        mvp_data = await self.bot.fetchrow("mvp_points", {
                            "user_id": member["user_id"],
                            "game": member["game"]
                        })

                        if mvp_data:
                            await self.bot.execute("mvp_points", "INCREMENT", {"votes": 1}, {
                                "_id": mvp_data["_id"]
                            })
                        else:
                            await self.bot.execute("mvp_points", "INSERT", {
                                "guild_id": vote["guild_id"],
                                "user_id": member["user_id"],
                                "votes": 1,
                                "game": member["game"]
                            })

                        await self.bot.execute("mvp_voting", "DELETE", None, {"_id": vote["_id"]})
                        await msg.channel.send(embed=embeds.success("Dziękujemy za głosowanie."))

    @Cog.listener('on_raw_member_remove')
    async def clear_member_data(self, payload):
        await self.bot.wait_until_ready()
        await self.bot.execute("game_member_data", "DELETE_MANY", None, {
            "user_id": payload.user.id,
            "channel_id": {"$in": [channel.id for channel in payload.guild.channels]}
        })
        games = await self.bot.fetch("games", {"guild_id": payload.guild.id})
        game_ids = [game["game_id"] for game in games]
        await self.bot.execute("ready_ups", "DELETE_MANY", None, {
            "user_id": payload.user.id,
            "game_id": {"$in": game_ids}
        })
        await self.bot.execute("igns", "DELETE_MANY", None, {
            "guild_id": payload.guild.id,
            "user_id": payload.user.id
        })
        await self.bot.execute("mvp_points", "DELETE_MANY", None, {
            "guild_id": payload.guild.id,
            "user_id": payload.user.id
        })
        await self.bot.execute("points", "DELETE_MANY", None, {
            "guild_id": payload.guild.id,
            "user_id": payload.user.id
        })
        await self.bot.execute("mmr_rating", "DELETE_MANY", None, {
            "guild_id": payload.guild.id,
            "user_id": payload.user.id
        })

def setup(bot):
    bot.add_cog(Events(bot))