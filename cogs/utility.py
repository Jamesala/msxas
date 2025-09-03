from disnake.ext.commands import Cog, slash_command, Param
from core.embeds import error, success

class Utility(Cog):
    """
    🛠️;Utility
    """
    def __init__(self, bot):
        self.bot = bot

    @slash_command()
    async def ign(self, ctx, ign, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Podaj swoją nazwę w grze.
        """
        data = await self.bot.fetchrow("igns", {"game": game, "user_id": ctx.author.id, "guild_id": ctx.guild.id})
        if data:
            return await ctx.send(embed=error("Już raz zarejestrowałeś swój IGN dla tej gry. Proszę o kontakt z administratorami."))

        await self.bot.execute("igns", "INSERT", {"guild_id": ctx.guild.id, "user_id": ctx.author.id, "game": game, "ign": ign})
        await ctx.send(embed=success("IGN skonfigurowano pomyślnie."))

def setup(bot):
    bot.add_cog(Utility(bot))