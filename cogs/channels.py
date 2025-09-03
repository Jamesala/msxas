from core import embeds, buttons, selectmenus
from disnake import TextChannel, Embed, Color, OptionChoice, SelectOption
from disnake.ext.commands import Cog, command, slash_command, Param

class ChannelCommands(Cog):
    """
    ⚙️;Channel Setup
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_slash_command_check(self, inter):
        if inter.author.guild_permissions.administrator:
            return True
        await inter.send(
            embed=embeds.error("You need to have **administrator** permission to run this command.")
        )
        return False

    async def cog_check(self, ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        await ctx.send(
            embed=embeds.error("You need to have **administrator** permission to run this command.")
        )
        return False

    @command(aliases=["channel"])
    async def setchannel(self, ctx, channel: TextChannel, game):
        if game.lower() not in ['lol', 'valorant', 'overwatch', 'spectre', 'marvel', 'other']:
            return await ctx.send(embed=embeds.error("Game has to be one of these: `valorant/lol/overwatch/spectre/marvel/other`."))

        data = await self.bot.fetchrow("queuechannels", {"channel_id": channel.id})
        if data:
            return await ctx.edit_original_message(
                embed=embeds.error(f"{channel.mention} is already setup as the queue channel.")
            )

        if game == 'lol':
            regions = ["BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]
        elif game == 'valorant':
            regions = ["EU", "NA", "BR", "KR", "AP", "LATAM"]
        elif game in ["overwatch", "spectre", "marvel"]:
            regions = ["AMERICAS", "ASIAS", "EUROPE"]
        else:
            regions = []

        if regions:
            options = [SelectOption(label=region, value=region.lower()) for region in regions]
            async def Function(inter, vals, *args):
                view = buttons.ConfirmationButtons(inter.author.id)
                await inter.edit_original_message(
                    embed=Embed(title=":warning: Notice", description=f"Messages in {channel.mention} will automatically be deleted to keep the queue channel clean, do you want to proceed?", color=Color.yellow()),
                    view=view,
                    content=""
                )
                await view.wait()
                if view.value is None or not view.value:
                    return await inter.edit_original_message(embed=embeds.success("Process aborted."))

                await self.bot.execute("queuechannels", "INSERT", {"channel_id": channel.id, "region": vals[0], "game": game})
                await inter.edit_original_message(
                    embed=embeds.success(f"{channel.mention} was successfully set as queue channel.")
                )

            await ctx.send(content="Select a region for the queue.", view=selectmenus.SelectMenuDeploy(self.bot, ctx.author.id, options, 1, 1, Function))
        else:
            await self.bot.execute("queuechannels", "INSERT", {"channel_id": channel.id, "region": "none", "game": game})
            await ctx.send(embed=embeds.success(f"{channel.mention} was successfully set as queue channel."))

    @slash_command(name="setchannel")
    async def setchannel_slash(self, ctx, channel: TextChannel, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Set a channel to be used as the queue.
        """
        await self.setchannel(ctx, channel, game)

    @command()
    async def setregion(self, ctx, queue_channel: TextChannel, region):
        if region.upper() not in ["BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]:
            return await ctx.send(embed=embeds.error("Please input a valid region."))

        data = await self.bot.fetchrow("queuechannels", {"channel_id": queue_channel.id, "game": "lol"})
        if not data:
            return await ctx.send(embed=embeds.error(f"{queue_channel.mention} is not a queue channel for league of legends."))

        await self.bot.execute("queuechannels", "UPDATE", {"region": region.lower()}, {"channel_id": queue_channel.id})
        await ctx.send(embed=embeds.success("Region for the queue channel updated successfully."))

    @slash_command(name="setregion")
    async def setregion_slash(self, ctx, queue_channel: TextChannel, region=Param(choices=[
        OptionChoice("EUW", "euw"), OptionChoice("NA", 'na'), OptionChoice("BR", 'br'),
        OptionChoice("EUNE", 'eune'), OptionChoice("LA", 'la'), OptionChoice("LAS", 'las'),
        OptionChoice("OCE", 'oce'), OptionChoice("RU", 'ru'), OptionChoice("TR", 'tr'), OptionChoice("JP", 'jp')
    ])):
        """
        Update a region for a league of legends queue channel.
        """
        await self.setregion(ctx, queue_channel, region)

    @command()
    async def setwinnerlog(self, ctx, channel: TextChannel, game):
        if game not in ['lol', 'valorant', 'overwatch', 'spectre', 'marvel', 'other']:
            return await ctx.send(embed=embeds.error("Please select a valid game. Game can be `lol/valorant/overwatch/spectre/marvel/other`."))

        data = await self.bot.fetchrow("winner_log_channel", {"channel_id": channel.id, "game": game})
        if data:
            return await ctx.send(embed=embeds.error(f"{channel.mention} is already setup as the match-history channel for this game."))

        await self.bot.execute("winner_log_channel", "INSERT", {"guild_id": ctx.guild.id, "channel_id": channel.id, "game": game})
        await ctx.send(embed=embeds.success(f"{channel.mention} was successfully set as match-history channel."))

    @slash_command(name="setwinnerlog")
    async def setwinnerlog_slash(self, ctx, channel: TextChannel, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Set a channel to send the game results.
        """
        await self.setwinnerlog(ctx, channel, game)

def setup(bot):
    bot.add_cog(ChannelCommands(bot))