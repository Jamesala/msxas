from disnake import Color, Embed, OptionChoice
from disnake.ext.commands import Cog, Param, command, slash_command
from Paginator import CreatePaginator
from core.embeds import error

class Leaderboard(Cog):
    """
    ⏫;Leaderboard
    """
    def __init__(self, bot):
        self.bot = bot

    async def leaderboard(self, ctx, game, member=None):
        if game not in ['lol', 'valorant', 'overwatch', 'spectre', 'marvel', 'other']:
            return await ctx.send(embed=error("Game has to be one of these: `valorant/lol/overwatch/spectre/marvel/other`."))

        user_data = await self.bot.fetch("points", {"guild_id": ctx.guild.id, "game": game})
        if not user_data:
            return await ctx.send(embed=error("There are no records to be displayed."))

        user_data = sorted(user_data, key=lambda x: x["wins"] / max(x["wins"] + x["losses"], 1), reverse=True)
        user_data = sorted(user_data, key=lambda x: x["wins"], reverse=True)

        embeds = []
        embed = Embed(title=f"🏆 Tabela liderów", color=Color.yellow())
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        async def add_field(data, i):
            user_history = await self.bot.fetch("members_history", {"user_id": data["user_id"], "game": game})
            if user_history and game != 'other':
                if game == 'lol':
                    roles_players = {'top': 0, 'jungle': 0, 'mid': 0, 'support': 0, 'adc': 0}
                elif game == 'valorant':
                    roles_players = {
                        'controller': 0, 'initiator': 0, 'sentinel': 0, 'duelist': 0, 'flex': 0,
                        'flex - controller': 0, 'flex - duelist': 0, 'flex - initiator': 0, 'flex - sentinel': 0
                    }
                elif game == "overwatch":
                    roles_players = {'tank': 0, 'dps 1': 0, 'dps 2': 0, 'support 1': 0, 'support 2': 0}
                elif game == "spectre":
                    roles_players = {'gracz 1': 0, 'gracz 2': 0, 'gracz 3': 0}
                elif game == "marvel":
                    roles_players = {'gracz 1': 0, 'gracz 2': 0, 'gracz 3': 0, 'gracz 4': 0, 'gracz 5': 0, 'gracz 6': 0}

                for history in user_history:
                    if history["role"]:
                        roles_players[history["role"]] += 1

                most_played_role = max(roles_players, key=lambda x: roles_players[x])
                most_played_role = self.bot.role_emojis[most_played_role] if roles_players[most_played_role] else "<:fill:1066868480537800714>"
            else:
                most_played_role = "<:fill:1066868480537800714>"

            st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": ctx.guild.id})
            if not st_pref:
                mmr_data = await self.bot.fetchrow("mmr_rating", {"user_id": data["user_id"], "guild_id": ctx.guild.id, "game": game})
                if mmr_data:
                    skill = float(mmr_data["mu"]) - (2 * float(mmr_data["sigma"]))
                    display_mmr = f"{int(skill*100)}" if mmr_data["counter"] >= 10 else f"{mmr_data['counter']}/10GP"
                else:
                    display_mmr = "0/10GP"
            else:
                display_mmr = ""

            name = "🥇" if i+1 == 1 else "🥈" if i+1 == 2 else "🥉" if i+1 == 3 else f"#{i+1}"
            member_obj = ctx.guild.get_member(data["user_id"])
            member_name = member_obj.name if member_obj else "Unknown Member"

            embed.add_field(
                name=name,
                value=f"{most_played_role} `{member_name}   {display_mmr} {data['wins']}W {data['losses']}L {round((data['wins'] / max(data['wins'] + data['losses'], 1)) * 100)}% WR`",
                inline=False
            )

        if member:
            for i, data in enumerate(user_data):
                if data["user_id"] == member.id:
                    await add_field(data, i)
                    embed.description = f"Statystyki dla {member.mention}"
                    return await ctx.send(embed=embed)
            return await ctx.send(embed=error(f"{member.mention} has no records in the {game} leaderboard."))

        for i, data in enumerate(user_data):
            if i % 10 == 0 and i != 0:
                embeds.append(embed)
                embed = Embed(title=f"🏆 Tabela liderów", color=Color.yellow())
                if ctx.guild.icon:
                    embed.set_thumbnail(url=ctx.guild.icon.url)
            await add_field(data, i)

        embeds.append(embed)
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            await ctx.send(embed=embeds[0], view=CreatePaginator(embeds, ctx.author.id))

    @slash_command()
    async def leaderboard(self, ctx, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Zobacz serwerową tablice wyników.
        """
        await self.leaderboard(ctx, game)

    @command()
    async def leaderboard(self, ctx, game):
        await self.leaderboard(ctx, game)

    @slash_command()
    async def rank(self, ctx, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Zobacz swój ranking na serwerze.
        """
        await self.leaderboard(ctx, game, ctx.author)

    @command()
    async def rank(self, ctx, game):
        await self.leaderboard(ctx, game, ctx.author)

    @slash_command()
    async def mvp(self, ctx, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Zobacz tablice wyników MVP serwera.
        """
        data = await self.bot.fetch("mvp_points", {"guild_id": ctx.guild.id, "game": game})
        if not data:
            return await ctx.send(embed=error("There are no MVP records to be displayed."))

        data = sorted(data, key=lambda x: x["votes"], reverse=True)
        embed = Embed(title="🏅 Tabela liderów MVP", color=Color.gold())
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        for i, d in enumerate(data[:10]):
            name = "🥇" if i+1 == 1 else "🥈" if i+1 == 2 else "🥉" if i+1 == 3 else f"#{i+1}"
            member = ctx.guild.get_member(d["user_id"])
            member_name = member.name if member else "Unknown Member"
            embed.add_field(
                name=name,
                value=f"`{member_name} - {d['votes']} votes`",
                inline=False
            )

        await ctx.send(embed=embed)

    @command()
    async def mvp(self, ctx, game):
        await self.mvp(ctx, game)

def setup(bot):
    bot.add_cog(Leaderboard(bot))