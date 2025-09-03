import random
from disnake import Color, Embed, ButtonStyle, Member
from disnake.ext.commands import Cog, slash_command, Param
from trueskill import Rating, backends, rate
from core.embeds import error, success
from core.buttons import ConfirmationButtons

class Win(Cog):
    """
    🏅;Win
    """
    def __init__(self, bot):
        self.bot = bot

    async def process_win(self, channel, user, admin=False, team=None):
        game_data = await self.bot.fetchrow("games", {"lobby_id": channel.id})
        if not game_data:
            return await channel.send(embed=error("Game not found."))

        member_data = await self.bot.fetch("game_member_data", {"game_id": game_data["game_id"]})
        if not member_data:
            return await channel.send(embed=error("No players found for this game."))

        if not admin:
            if team not in ["red", "blue"]:
                return await channel.send(embed=error("Invalid team selected."))

            await self.bot.execute("members_history", "UPDATE", {"voted_team": team}, {"user_id": user.id, "game_id": game_data["game_id"]})
            votes = await self.bot.fetch("members_history", {"game_id": game_data["game_id"], "voted_team": team})
            required_votes = 3 if game_data["game"] == "spectre" else 6 if game_data["game"] == "marvel" else 5

            if len(votes) < required_votes:
                return await channel.send(embed=success(f"Your vote for {team.capitalize()} team has been recorded."))

        winner_team = team if admin else votes[0]["voted_team"]
        winner_rating = []
        loser_rating = []
        for member in member_data:
            mmr_data = await self.bot.fetchrow("mmr_rating", {"user_id": member["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
            rating = Rating(mu=float(mmr_data["mu"]) if mmr_data else 25.0, sigma=float(mmr_data["sigma"]) if mmr_data else 8.33333333333333)

            if member["team"] == winner_team:
                await self.bot.execute("members_history", "UPDATE", {"result": "won"}, {"user_id": member["user_id"], "game_id": game_data["game_id"]})
                points_data = await self.bot.fetchrow("points", {"user_id": member["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
                wins = points_data["wins"] + 1 if points_data else 1
                losses = points_data["losses"] if points_data else 0
                await self.bot.execute("points", "UPDATE", {"wins": wins, "losses": losses}, {"user_id": member["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
                winner_rating.append({"user_id": member["user_id"], "rating": rating})
            else:
                await self.bot.execute("members_history", "UPDATE", {"result": "lost"}, {"user_id": member["user_id"], "game_id": game_data["game_id"]})
                points_data = await self.bot.fetchrow("points", {"user_id": member["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
                wins = points_data["wins"] if points_data else 0
                losses = points_data["losses"] + 1 if points_data else 1
                await self.bot.execute("points", "UPDATE", {"wins": wins, "losses": losses}, {"user_id": member["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
                loser_rating.append({"user_id": member["user_id"], "rating": rating})

        backends.choose_backend("mpmath")
        updated_rating = rate([[x['rating'] for x in winner_rating], [x['rating'] for x in loser_rating]], ranks=[0, 1])

        for i, new_rating in enumerate(updated_rating[0]):
            counter_data = await self.bot.fetchrow("mmr_rating", {"user_id": winner_rating[i]["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
            counter = counter_data["counter"] + 1 if counter_data else 1
            await self.bot.execute("mmr_rating", "UPDATE", {
                "mu": str(new_rating.mu),
                "sigma": str(new_rating.sigma),
                "counter": counter
            }, {"user_id": winner_rating[i]["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
            await self.bot.execute("members_history", "UPDATE", {
                "now_mmr": f"{str(new_rating.mu)}:{str(new_rating.sigma)}"
            }, {"user_id": winner_rating[i]["user_id"], "game_id": game_data["game_id"]})

        for i, new_rating in enumerate(updated_rating[1]):
            counter_data = await self.bot.fetchrow("mmr_rating", {"user_id": loser_rating[i]["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
            counter = counter_data["counter"] + 1 if counter_data else 1
            await self.bot.execute("mmr_rating", "UPDATE", {
                "mu": str(new_rating.mu),
                "sigma": str(new_rating.sigma),
                "counter": counter
            }, {"user_id": loser_rating[i]["user_id"], "guild_id": channel.guild.id, "game": game_data["game"]})
            await self.bot.execute("members_history", "UPDATE", {
                "now_mmr": f"{str(new_rating.mu)}:{str(new_rating.sigma)}"
            }, {"user_id": loser_rating[i]["user_id"], "game_id": game_data["game_id"]})

        log_channel_data = await self.bot.fetchrow("winner_log_channel", {"guild_id": channel.guild.id, "game": game_data["game"]})
        if log_channel_data:
            log_channel = self.bot.get_channel(log_channel_data["channel_id"])
            if log_channel:
                mentions = (
                    f"🔴 Red Team: " + ", ".join(f"<@{data['user_id']}>" for data in member_data if data["team"] == "red") +
                    "\n🔵 Blue Team: " + ", ".join(f"<@{data['user_id']}>" for data in member_data if data["team"] == "blue")
                )
                embed = Embed(
                    title=f"Wyniki gry!",
                    description=f"Gratulacje dla **{winner_team.capitalize()} Team** za wygraną w grze **{game_data['game_id']}**!",
                    color=Color.green(),
                )
                await log_channel.send(mentions, embed=embed)

        for member in member_data:
            await self.bot.execute("mvp_voting", "INSERT", {
                "guild_id": channel.guild.id,
                "user_id": member["user_id"],
                "game_id": game_data["game_id"]
            })

        mvp_embed = Embed(
            title="Głosowanie na MVP",
            description="Każdy gracz powinien otrzymać prywatną wiadomość od bota, aby zagłosować na MVP meczu. Wybierz numer gracza, którego uważasz za najlepszego w meczu.",
            color=Color.gold()
        )
        for i, member in enumerate(member_data):
            mvp_embed.add_field(
                name=f"Gracz {i+1}",
                value=f"<@{member['user_id']}> - {member['role'].capitalize()}",
                inline=False
            )
        await channel.send(embed=mvp_embed)

        try:
            red_channel = self.bot.get_channel(game_data["red_channel_id"])
            await red_channel.delete()
            blue_channel = self.bot.get_channel(game_data["blue_channel_id"])
            await blue_channel.delete()
            red_role = channel.guild.get_role(game_data["red_role_id"])
            await red_role.delete()
            blue_role = channel.guild.get_role(game_data["blue_role_id"])
            await blue_role.delete()
            await channel.delete()
            category = channel.category
            if len(category.channels) == 1:
                await category.delete()
        except:
            await channel.send(embed=error("Unable to delete game channels and roles, please remove them manually."))

        await self.bot.execute("games", "DELETE", None, {"game_id": game_data["game_id"]})
        await self.bot.execute("game_member_data", "DELETE_MANY", None, {"game_id": game_data["game_id"]})
        await self.bot.execute("ready_ups", "DELETE_MANY", None, {"game_id": game_data["game_id"]})

    @slash_command()
    async def win(self, ctx, team=Param(choices=[OptionChoice("Red", "red"), OptionChoice("Blue", "blue")])):
        """
        Zagłosuj na zwycięską drużynę.
        """
        member_data = await self.bot.fetchrow("game_member_data", {"user_id": ctx.author.id})
        if not member_data:
            return await ctx.send(embed=error("You are not in any game."))

        game_data = await self.bot.fetchrow("games", {"game_id": member_data["game_id"]})
        if not game_data:
            return await ctx.send(embed=error("Game not found."))

        if ctx.channel.id != game_data["lobby_id"]:
            return await ctx.send(embed=error("Please use this command in the game lobby channel."))

        await self.process_win(ctx.channel, ctx.author, False, team)

def setup(bot):
    bot.add_cog(Win(bot))