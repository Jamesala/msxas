from disnake import Color, Embed, Member, OptionChoice, Role, TextChannel, PermissionOverwrite, SelectOption
from disnake.ext.commands import Cog, Context, Param, group, slash_command
from trueskill import Rating, backends, rate
from cogs.win import Win
from core.embeds import error, success
from core.buttons import ConfirmationButtons, LinkButton
from core.selectmenus import SelectMenuDeploy
from core.match import start_queue

async def leaderboard_persistent(bot, channel, game):
    user_data = await bot.fetch("points", {"guild_id": channel.guild.id, "game": game})
    if user_data:
        user_data = sorted(user_data, key=lambda x: x["wins"] / max(x["wins"] + x["losses"], 1), reverse=True)
        user_data = sorted(user_data, key=lambda x: x["wins"], reverse=True)

    embed = Embed(title="Tabela liderow", color=Color.yellow())
    if channel.guild.icon:
        embed.set_thumbnail(url=channel.guild.icon.url)

    async def add_field(data, i):
        user_history = await bot.fetch("members_history", {"user_id": data["user_id"], "game": game})
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
            most_played_role = bot.role_emojis[most_played_role] if roles_players[most_played_role] else "<:fill:1066868480537800714>"
        else:
            most_played_role = "<:fill:1066868480537800714>"

        st_pref = await bot.fetchrow("switch_team_preference", {"guild_id": channel.guild.id})
        if not st_pref:
            mmr_data = await bot.fetchrow("mmr_rating", {"user_id": data["user_id"], "guild_id": channel.guild.id, "game": game})
            if mmr_data:
                skill = float(mmr_data["mu"]) - (2 * float(mmr_data["sigma"]))
                display_mmr = f"{int(skill*100)}" if mmr_data["counter"] >= 10 else f"{mmr_data['counter']}/10GP"
            else:
                display_mmr = "0/10GP"
        else:
            display_mmr = ""

        name = "??" if i+1 == 1 else "??" if i+1 == 2 else "??" if i+1 == 3 else f"#{i+1}"
        member = channel.guild.get_member(data["user_id"])
        member_name = member.name if member else "Unknown Member"

        embed.add_field(
            name=name,
            value=f"{most_played_role} `{member_name}   {display_mmr} {data['wins']}W {data['losses']}L {round((data['wins'] / max(data['wins'] + data['losses'], 1)) * 100)}% WR`",
            inline=False
        )

    if not user_data:
        embed.description = "Nie ma jeszcze zadnych rekordow do wyswietlenia."
    for i, data in enumerate(user_data[:10]):
        await add_field(data, i)

    return embed

class Admin(Cog):
    """
    ??;Admin
    """
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx: Context) -> bool:
        if ctx.author.guild_permissions.administrator:
            return True
        if ctx.command.qualified_name in ['admin', 'admin reset']:
            return True

        author_role_ids = [r.id for r in ctx.author.roles]
        admin_enable = await self.bot.fetch("admin_enables", {"guild_id": ctx.guild.id, "command": ctx.command.qualified_name})
        for data in admin_enable:
            if data["role_id"] in author_role_ids:
                return True

        await ctx.send(embed=error("You need **administrator** permissions to use this command."))
        return False

    async def cog_slash_command_check(self, inter) -> bool:
        if inter.author.guild_permissions.administrator:
            return True
        if inter.application_command.qualified_name in ['admin', 'admin reset']:
            return True

        author_role_ids = [r.id for r in inter.author.roles]
        admin_enable = await self.bot.fetch("admin_enables", {"guild_id": inter.guild.id, "command": inter.application_command.qualified_name})
        for data in admin_enable:
            if data["role_id"] in author_role_ids:
                return True

        await inter.send(embed=error("You need **administrator** permissions to use this command."))
        return False

    @group()
    async def admin(self, ctx):
        pass

    @admin.command()
    async def user_dequeue(self, ctx, member: Member):
        member_data = await self.bot.fetch("game_member_data", {"user_id": member.id})
        for entry in member_data:
            game_data = await self.bot.fetchrow("games", {"game_id": entry["game_id"]})
            if not game_data:
                await self.bot.execute("game_member_data", "DELETE_MANY", None, {"user_id": member.id})
                await self.bot.execute("ready_ups", "DELETE_MANY", None, {"game_id": entry["game_id"]})

        await ctx.send(embed=success(f"{member.mention} was removed from all active queues. They may still show up in queue embed."))

    @admin.command()
    async def winner(self, ctx, role: Role):
        role_name = role.name
        game_id = role_name.replace("Red: ", "").replace("Blue: ", "")
        game_data = await self.bot.fetchrow("games", {"game_id": game_id})

        if game_data:
            team = "red" if "Red" in role_name else "blue"
            await ctx.send(embed=success(f"Game **{game_id}** was concluded."))
            channel = self.bot.get_channel(game_data["lobby_id"])
            await Win.process_win(self, channel, ctx.author, True, team)
        else:
            await ctx.send(embed=error("Game was not found."))

    @admin.command()
    async def change_winner(self, ctx, game_id: str, team: str):
        if team.lower() not in ["red", "blue"]:
            return await ctx.send(embed=error("Invalid team input received."))

        member_data = await self.bot.fetch("members_history", {"game_id": game_id})
        if not member_data:
            return await ctx.send(embed=error(f"Game **{game_id}** was not found."))

        for member in member_data:
            if member["result"] == "won" and member["team"] == team.lower():
                return await ctx.send(embed=error(f"{team.capitalize()} is already the winner."))

        wrong_voters = []
        winner_rating = []
        loser_rating = []
        for member_entry in member_data:
            user_data = await self.bot.fetchrow("points", {"user_id": member_entry["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
            if member_entry["voted_team"] != "none" and member_entry["voted_team"] != team.lower():
                wrong_voters.append(member_entry["user_id"])

            rating = Rating(mu=float(member_entry["old_mmr"].split(':')[0]), sigma=float(member_entry["old_mmr"].split(':')[1]))

            if member_entry["team"] == team.lower():
                await self.bot.execute("members_history", "UPDATE", {"result": "won"}, {"user_id": member_entry["user_id"], "game_id": game_id})
                wins = user_data["wins"] + 1 if user_data else 1
                losses = user_data["losses"] - 1 if user_data and user_data["losses"] > 0 else 0
                await self.bot.execute("points", "UPDATE", {"wins": wins, "losses": losses}, {"user_id": member_entry["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
                winner_rating.append({"user_id": member_entry["user_id"], "rating": rating})
            else:
                await self.bot.execute("members_history", "UPDATE", {"result": "lost"}, {"user_id": member_entry["user_id"], "game_id": game_id})
                wins = user_data["wins"] - 1 if user_data and user_data["wins"] > 0 else 0
                losses = user_data["losses"] + 1 if user_data else 1
                await self.bot.execute("points", "UPDATE", {"wins": wins, "losses": losses}, {"user_id": member_entry["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
                loser_rating.append({"user_id": member_entry["user_id"], "rating": rating})

        backends.choose_backend("mpmath")
        updated_rating = rate([[x['rating'] for x in winner_rating], [x['rating'] for x in loser_rating]], ranks=[0, 1])

        for i, new_rating in enumerate(updated_rating[0]):
            counter_data = await self.bot.fetchrow("mmr_rating", {"user_id": winner_rating[i]["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
            counter = counter_data["counter"] + 1 if counter_data else 1
            await self.bot.execute("mmr_rating", "UPDATE", {
                "mu": str(new_rating.mu),
                "sigma": str(new_rating.sigma),
                "counter": counter
            }, {"user_id": winner_rating[i]["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
            await self.bot.execute("members_history", "UPDATE", {
                "now_mmr": f"{str(new_rating.mu)}:{str(new_rating.sigma)}"
            }, {"user_id": winner_rating[i]["user_id"], "game_id": game_id})

        for i, new_rating in enumerate(updated_rating[1]):
            counter_data = await self.bot.fetchrow("mmr_rating", {"user_id": loser_rating[i]["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
            counter = counter_data["counter"] + 1 if counter_data else 1
            await self.bot.execute("mmr_rating", "UPDATE", {
                "mu": str(new_rating.mu),
                "sigma": str(new_rating.sigma),
                "counter": counter
            }, {"user_id": loser_rating[i]["user_id"], "guild_id": ctx.guild.id, "game": member_entry["game"]})
            await self.bot.execute("members_history", "UPDATE", {
                "now_mmr": f"{str(new_rating.mu)}:{str(new_rating.sigma)}"
            }, {"user_id": loser_rating[i]["user_id"], "game_id": game_id})

        if wrong_voters:
            wrong_voters_embed = Embed(
                title="Wrong Voters",
                description="These player(s) purposely voted for the wrong winning team.\n" + "\n".join(f"{i+1}. <@{x}>" for i, x in enumerate(wrong_voters)),
                color=Color.yellow()
            )
            await ctx.send(embeds=[success("Game winner was changed."), wrong_voters_embed])
        else:
            await ctx.send(embed=success("Game winner was changed."))

        log_channel_data = await self.bot.fetchrow("winner_log_channel", {"guild_id": ctx.guild.id, "game": member_entry["game"]})
        if log_channel_data:
            log_channel = self.bot.get_channel(log_channel_data["channel_id"])
            if log_channel:
                mentions = (
                    f"?? Red Team: " + ", ".join(f"<@{data['user_id']}>" for data in member_data if data["team"] == "red") +
                    "\n?? Blue Team: " + ", ".join(f"<@{data['user_id']}>" for data in member_data if data["team"] == "blue")
                )
                embed = Embed(
                    title=f"Wyniki gry uleg?y zmianie!",
                    description=f"Wynik gry **{game_id}** zosta? zmieniony!\n\nWynik: **{team.capitalize()} Team wygra?!**",
                    color=Color.blurple(),
                )
                await log_channel.send(mentions, embed=embed)

    @admin.command()
    async def void(self, ctx, game_id):
        game_data = await self.bot.fetchrow("games", {"game_id": game_id})
        if not game_data:
            return await ctx.send(embed=error("Nie znaleziono gry."))

        await self.bot.execute("games", "DELETE", None, {"game_id": game_id})
        await self.bot.execute("game_member_data", "DELETE_MANY", None, {"game_id": game_id})
        await self.bot.execute("ready_ups", "DELETE_MANY", None, {"game_id": game_id})

        try:
            for category in ctx.guild.categories:
                if category.name == f"Game: {game_data['game_id']}":
                    await category.delete()
            red_channel = self.bot.get_channel(game_data["red_channel_id"])
            await red_channel.delete()
            blue_channel = self.bot.get_channel(game_data["blue_channel_id"])
            await blue_channel.delete()
            red_role = ctx.guild.get_role(game_data["red_role_id"])
            await red_role.delete()
            blue_role = ctx.guild.get_role(game_data["blue_role_id"])
            await blue_role.delete()
            lobby = self.bot.get_channel(game_data["lobby_id"])
            await lobby.delete()
        except:
            await ctx.send(embed=error("Unable to delete game channels and roles, please remove them manually."))

        await ctx.send(embed=success(f"All records for Game **{game_id}** were deleted."))

    @admin.command()
    async def cancel(self, ctx, member: Member):
        member_data = await self.bot.fetchrow("game_member_data", {"user_id": member.id})
        if member_data:
            game_id = member_data["game_id"]
            game_data = await self.bot.fetchrow("games", {"game_id": game_id})
            for category in ctx.guild.categories:
                if category.name == f"Game: {game_data['game_id']}":
                    await category.delete()
            red_channel = self.bot.get_channel(game_data["red_channel_id"])
            await red_channel.delete()
            blue_channel = self.bot.get_channel(game_data["blue_channel_id"])
            await blue_channel.delete()
            red_role = ctx.guild.get_role(game_data["red_role_id"])
            await red_role.delete()
            blue_role = ctx.guild.get_role(game_data["blue_role_id"])
            await blue_role.delete()
            lobby = self.bot.get_channel(game_data["lobby_id"])
            await lobby.delete()
            await self.bot.execute("games", "DELETE", None, {"game_id": game_id})
            await self.bot.execute("game_member_data", "DELETE_MANY", None, {"game_id": game_id})
            await ctx.send(embed=success(f"Game **{game_id}** was successfully cancelled."))
        else:
            await ctx.send(embed=error(f"{member.mention} is not a part of any ongoing games."))

    @admin.group()
    async def reset(self, ctx):
        pass

    @reset.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        data = await self.bot.fetch("points", {"guild_id": ctx.guild.id})
        if not data:
            return await ctx.send(embed=error("There are no records to be deleted"))

        view = ConfirmationButtons(ctx.author.id)
        await ctx.send("This will reset all member's wins, losses, MMR and MVP votes back to 0. Are you sure?", view=view)
        await view.wait()
        if view.value:
            await self.bot.execute("mvp_points", "UPDATE_MANY", {"votes": 0}, {"guild_id": ctx.guild.id})
            await self.bot.execute("points", "UPDATE_MANY", {"wins": 0, "losses": 0}, {"guild_id": ctx.guild.id})
            await self.bot.execute("mmr_rating", "UPDATE_MANY", {"counter": 0, "mu": 25.0, "sigma": 8.33333333333333}, {"guild_id": ctx.guild.id})
            await ctx.send(embed=success("Successfully reset all wins, mmr and mvp votes"))
        else:
            await ctx.send(embed=success("Process aborted."))

    @reset.command()
    async def queue(self, ctx, game_id):
        game_data = await self.bot.fetchrow("games", {"game_id": game_id})
        if game_data:
            return await ctx.send(embed=error("You cannot reset an ongoing game. To cancel an ongoing game, please use `/admin cancel [member]`"))

        member_data = await self.bot.fetchrow("game_member_data", {"game_id": game_id})
        if member_data:
            await self.bot.execute("game_member_data", "DELETE_MANY", None, {"game_id": game_id})
            await ctx.send(embed=success(f"Game **{game_id}** queue was refreshed."))
        else:
            await ctx.send(embed=error(f"Game **{game_id}** was not found."))

    @reset.command()
    async def user(self, ctx, member: Member):
        data = await self.bot.fetch("points", {"guild_id": ctx.guild.id, "user_id": member.id})
        if not data:
            return await ctx.send(embed=error("There are no records to be deleted"))

        view = ConfirmationButtons(ctx.author.id)
        await ctx.send(f"This will reset all {member.display_name}'s wins, losses, MMR and MVP votes back to 0. Are you sure?", view=view)
        await view.wait()
        if view.value:
            await self.bot.execute("mvp_points", "UPDATE_MANY", {"votes": 0}, {"guild_id": ctx.guild.id, "user_id": member.id})
            await self.bot.execute("points", "UPDATE_MANY", {"wins": 0, "losses": 0}, {"guild_id": ctx.guild.id, "user_id": member.id})
            await self.bot.execute("mmr_rating", "UPDATE_MANY", {"counter": 0, "mu": 25.0, "sigma": 8.33333333333333}, {"guild_id": ctx.guild.id, "user_id": member.id})
            await ctx.send(embed=success(f"Successfully reset all wins, mmr and mvp votes of {member.display_name}"))
        else:
            await ctx.send(embed=success("Process aborted."))

    @slash_command(name="admin")
    async def admin_slash(self, ctx):
        pass

    @admin_slash.sub_command()
    async def grant(self, ctx, role: Role, command=Param(choices=[
        OptionChoice('Reset server leaderboard', 'admin reset leaderboard'),
        OptionChoice('Remove users from queue', 'admin user_dequeue'),
        OptionChoice('Reset a queue', 'admin reset queue'),
        OptionChoice('Change results of a game', 'admin change_winner'),
        OptionChoice('Force a winner', 'admin winner'),
        OptionChoice('Cancel a game', 'admin cancel'),
        OptionChoice('Void Game', 'admin void'),
        OptionChoice('Enable/Disable MMR', 'admin sbmm'),
        OptionChoice('Create a dynamic leaderboard', 'admin top_ten'),
        OptionChoice('Set queue preferences', 'admin queue_preference'),
        OptionChoice('Enable/Disable Duo queue', 'admin duo_queue'),
        OptionChoice('Update members IGN', 'admin update_ign'),
        OptionChoice('Enable/Disable test mode', 'admin test_mode')
    ])):
        """
        Zezwalaj roli na uruchamianie okre?lonego polecenia administratora.
        """
        data = await self.bot.fetchrow("admin_enables", {"guild_id": ctx.guild.id, "role_id": role.id, "command": command})
        if data:
            return await ctx.send(embed=error(f"{role.mention} already has access to the command."))

        await self.bot.execute("admin_enables", "INSERT", {"guild_id": ctx.guild.id, "command": command, "role_id": role.id})
        await ctx.send(embed=success(f"Command enabled for {role.mention} successfully."))

    @admin_slash.sub_command()
    async def revoke(self, ctx, role: Role, command=Param(choices=[
        OptionChoice('Reset tabeli lider\u00f3w', 'admin reset leaderboard'),
        OptionChoice('Usu里 u?ytkownik車w z kolejki', 'admin user_dequeue'),
        OptionChoice('Zresetuj kolejk?', 'admin reset queue'),
        OptionChoice('Zmie里 wyniki gry', 'admin change_winner'),
        OptionChoice('Wymusi? zwyci?zc?', 'admin winner'),
        OptionChoice('Anuluj gr?', 'admin cancel'),
        OptionChoice('Wyczy?? gre', 'admin void'),
        OptionChoice('Enable/Disable MMR', 'admin sbmm'),
        OptionChoice('Create dynamic leaderboard', 'admin top_ten'),
        OptionChoice('Set queue preference', 'admin queue_preference'),
        OptionChoice('Enable/Disable duo queue', 'admin duo_queue'),
        OptionChoice('Update members IGN', 'admin update_ign'),
        OptionChoice('Enable/Disable test mode', 'admin test_mode')
    ])):
        """
        Disallow a role to run a admin command.
        """
        data = await self.bot.fetchrow("admin_enables", {"guild_id": ctx.guild.id, "role_id": role.id, "command": command})
        if not data:
            return await ctx.send(embed=error(f"{role.mention} already does not have access to the command."))

        await self.bot.execute("admin_enables", "DELETE", None, {"guild_id": ctx.guild.id, "command": command, "role_id": role.id})
        await ctx.send(embed=success(f"Command disabled for {role.mention} successfully."))

    @admin_slash.sub_command(name="user_dequeue")
    async def user_dequeue_slash(self, ctx, member: Member):
        """
        Usu里 u?ytkownika ze wszystkich kolejek. Do??cz ponownie do kolejki, aby od?wie?y? lobby.
        """
        await self.user_dequeue(ctx, member)

    @admin_slash.sub_command()
    async def queue_preference(self, ctx, preference=Param(choices=[OptionChoice("Multi Queue", "1"), OptionChoice("Single Queue", "2")])):
        """
        Decide if players can be in multiple queues at once
        """
        preference_data = await self.bot.fetchrow("queue_preference", {"guild_id": ctx.guild.id})
        if preference_data:
            await self.bot.execute("queue_preference", "UPDATE", {"preference": int(preference)}, {"guild_id": ctx.guild.id})
        else:
            await self.bot.execute("queue_preference", "INSERT", {"guild_id": ctx.guild.id, "preference": int(preference)})
        await ctx.send(embed=success("Preference updated successfully."))

    @admin_slash.sub_command(name="change_winner")
    async def change_winner_slash(self, ctx, game_id, team=Param(choices=[OptionChoice("Red", "red"), OptionChoice("Blue", "blue")])):
        """
        Zmie里 zwyci?zc? uko里czonej gry.
        """
        await self.change_winner(ctx, game_id, team)

    @admin_slash.sub_command(name="winner")
    async def winner_slash(self, ctx, role: Role):
        """
        Og?o? zwyci?zc? gry. Pomija g?osowanie. Gra musi by? w toku.
        """
        await self.winner(ctx, role)

    @admin_slash.sub_command(name="cancel")
    async def cancel_slash(self, ctx, member: Member):
        """
        Anuluj gr? cz?onka.
        """
        await self.cancel(ctx, member)

    @admin_slash.sub_command(name="top_ten")
    async def leaderboard_persistent_slash(self, ctx, channel: TextChannel, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Create a Dynamic Top 10 leaderboard
        """
        embed = await leaderboard_persistent(self.bot, channel, game)
        msg = await channel.send(embed=embed)
        if not msg:
            return await ctx.send(embed=error("Brak rekord車w do wy?wietlenia w tabeli lider車w. Spr車buj najpierw rozegra? mecz."))
        data = await self.bot.fetchrow("persistent_lb", {"guild_id": ctx.guild.id, "game": game})
        if data:
            await self.bot.execute("persistent_lb", "UPDATE", {"channel_id": channel.id, "msg_id": msg.id}, {"guild_id": ctx.guild.id, "game": game})
        else:
            await self.bot.execute("persistent_lb", "INSERT", {"guild_id": ctx.guild.id, "channel_id": channel.id, "msg_id": msg.id, "game": game})
        await ctx.send(embed=success("Persistent leaderboard activated successfully."))

    @admin_slash.sub_command(name="void")
    async def void_slash(self, ctx, game_id):
        """
        Purge all records of a game. Use with care.
        """
        await self.void(ctx, game_id)

    @admin_slash.sub_command(name="sbmm")
    async def sbmm(self, ctx, preference=Param(choices=[OptionChoice('Enabled', '1'), OptionChoice('Disabled', '0')])):
        """
        Enable/Disable SkillBased match making.
        """
        if int(preference):
            await self.bot.execute("switch_team_preference", "DELETE", None, {"guild_id": ctx.guild.id})
        else:
            await self.bot.execute("switch_team_preference", "INSERT", {"guild_id": ctx.guild.id})
        await ctx.send(embed=success(f"SBMM preference changed successfully."))

    @admin_slash.sub_command()
    async def duo_queue(self, ctx, preference=Param(choices=[OptionChoice('Enabled', '1'), OptionChoice('Disabled', '0')])):
        """
        Enable/Disable Duo Queue system.
        """
        sbmm = await self.bot.fetchrow("switch_team_preference", {"guild_id": ctx.guild.id})
        if sbmm:
            return await ctx.send(embed=error("Please enable sbmm to Duo. `/admin sbmm Enabled`"))
        if int(preference):
            await self.bot.execute("duo_queue_preference", "INSERT", {"guild_id": ctx.guild.id})
        else:
            await self.bot.execute("duo_queue_preference", "DELETE", None, {"guild_id": ctx.guild.id})
        await ctx.send(embed=success(f"Duo Queue preference changed successfully."))

    @admin_slash.sub_command()
    async def test_mode(self, ctx, condition: bool):
        """
        Enable/Disable InHouseQueue for test mode.
        """
        data = await self.bot.fetchrow("testmode", {"guild_id": ctx.guild.id})
        if data and condition:
            return await ctx.send(embed=success("Test mode is already enabled."))
        if not data and not condition:
            return await ctx.send(embed=success("Test mode is already disabled."))
        if condition:
            await self.bot.execute("testmode", "INSERT", {"guild_id": ctx.guild.id})
            await ctx.send(embed=success("Test mode enabled successfully."))
        else:
            await self.bot.execute("testmode", "DELETE", None, {"guild_id": ctx.guild.id})
            await ctx.send(embed=success("Test mode disabled successfully."))

    @admin_slash.sub_command()
    async def setup(self, ctx, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Setup InHouse Queue in your server.
        """
        if game == 'lol':
            regions = ["BR", "EUNE", "EUW", "LA", "LAS", "NA", "OCE", "RU", "TR", "JP"]
        elif game == 'valorant':
            regions = ["EU", "NA", "BR", "KR", "AP", "LATAM"]
        elif game in ["overwatch", "spectre", "marvel"]:
            regions = ["AMERICAS", "ASIAS", "EUROPE"]
        else:
            regions = []

        async def process_setup(region):
            mutual_overwrites = {
                ctx.guild.default_role: PermissionOverwrite(send_messages=False),
                self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True),
            }
            display_game = {
                "lol": "League Of Legends",
                "valorant": "Valorant",
                "spectre": "Spectre Divide",
                "marvel": "Marvel Rivals",
                "overwatch": "Overwatch",
                "other": "Other"
            }.get(game, "Other")
            category = await ctx.guild.create_category(name=f"MIXY - {display_game}", overwrites=mutual_overwrites)
            queue = await category.create_text_channel(name="kolejka")
            match_history = await category.create_text_channel(name="historia-meczy")
            top_ten = await category.create_text_channel(name="top-10")
            await self.bot.execute("queuechannels", "INSERT", {"channel_id": queue.id, "region": region, "game": game})
            winnerlog = await self.bot.fetchrow("winner_log_channel", {"guild_id": ctx.guild.id, "game": game})
            if winnerlog:
                await self.bot.execute("winner_log_channel", "UPDATE", {"channel_id": match_history.id}, {"guild_id": ctx.guild.id, "game": game})
            else:
                await self.bot.execute("winner_log_channel", "INSERT", {"guild_id": ctx.guild.id, "channel_id": match_history.id, "game": game})
            embed = await leaderboard_persistent(self.bot, top_ten, game)
            msg = await top_ten.send(embed=embed)
            data = await self.bot.fetchrow("persistent_lb", {"guild_id": ctx.guild.id, "game": game})
            if data:
                await self.bot.execute("persistent_lb", "UPDATE", {"channel_id": top_ten.id, "msg_id": msg.id}, {"guild_id": ctx.guild.id, "game": game})
            else:
                await self.bot.execute("persistent_lb", "INSERT", {"guild_id": ctx.guild.id, "channel_id": top_ten.id, "msg_id": msg.id, "game": game})
            await start_queue(self.bot, queue, game)
            embed = Embed(description="Historie meczow beda publikowane tutaj!", color=Color.red())
            await match_history.send(embed=embed)
            overwrites = {
                ctx.guild.default_role: PermissionOverwrite(send_messages=False),
                self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True),
            }
            category = await ctx.guild.create_category(name=f"Obecne Mecze {game}", overwrites=overwrites)
            cate_data = await self.bot.fetchrow("game_categories", {"guild_id": ctx.guild.id, "game": game})
            if cate_data:
                await self.bot.execute("game_categories", "UPDATE", {"category_id": category.id}, {"guild_id": ctx.guild.id, "game": game})
            else:
                await self.bot.execute("game_categories", "INSERT", {"guild_id": ctx.guild.id, "category_id": category.id, "game": game})
            info_channel = await category.create_text_channel("Informacje")
            embed = Embed(title="Kolejka MIXY", description=f"Wszystkie {display_game} w toku gry b?d? znajdowa? si? w tej tutaj.", color=Color.red())
            embed.set_image(url="https://i.imgur.com/ljehx2G.png")
            view = LinkButton({"Strona": "https://discordzik.pl"})
            await info_channel.send(embed=embed, view=view)
            await ctx.send(embed=success("Setup completed successfully. If any, please delete previous 'match-history', 'top_10' and 'information' text channels. These are now inactive."))

        if regions:
            options = [SelectOption(label=region, value=region.lower()) for region in regions]
            async def Function(inter, vals, *args):
                await process_setup(vals[0])
            await ctx.send(content="Select a region for the queue.", view=SelectMenuDeploy(self.bot, ctx.author.id, options, 1, 1, Function))
        else:
            await process_setup("none")

    @admin_slash.sub_command()
    async def reset_db(self, ctx, user_id):
        """
        Remove entries of a user from the leaderboards.
        """
        try:
            await self.bot.execute("points", "DELETE_MANY", None, {"user_id": int(user_id), "guild_id": ctx.guild.id})
            await self.bot.execute("mvp_points", "DELETE_MANY", None, {"user_id": int(user_id), "guild_id": ctx.guild.id})
            await self.bot.execute("mmr_rating", "DELETE_MANY", None, {"user_id": int(user_id), "guild_id": ctx.guild.id})
            await ctx.send(embed=success("Successfully deleted entries associated with the given ID."))
        except:
            await ctx.send(embed=error("An error occurred. Please recheck the user ID."))

    @admin_slash.sub_command()
    async def update_ign(self, ctx, ign, member: Member, game=Param(choices={"League Of Legends": "lol", "Valorant": "valorant", "Overwatch": "overwatch", "Spectre Divide": "spectre", "Marvel Rivals": "marvel", "Other": "other"})):
        """
        Update In game name of a player
        """
        data = await self.bot.fetchrow("igns", {"game": game, "user_id": member.id, "guild_id": ctx.guild.id})
        if data:
            await self.bot.execute("igns", "UPDATE", {"ign": ign}, {"guild_id": ctx.guild.id, "user_id": member.id, "game": game})
        else:
            await self.bot.execute("igns", "INSERT", {"guild_id": ctx.guild.id, "user_id": member.id, "game": game, "ign": ign})
        await ctx.send(embed=success("IGN updated successfully."))

    @admin_slash.sub_command_group(name="reset")
    async def reset_slash(self, ctx):
        pass

    @reset_slash.sub_command(name="leaderboard")
    async def leaderboard_slash(self, ctx):
        """
        Reset your entire servers Wins, Losses, MMR and MVP votes back to 0.
        """
        await self.leaderboard(ctx)

    @reset_slash.sub_command(name="queue")
    async def queue_slash(self, ctx, game_id: str):
        """
        Usu里 wszystkich z kolejki. Do??cz ponownie do kolejki, aby od?wie?y? lobby.
        """
        await self.queue(ctx, game_id)

    @reset_slash.sub_command(name="user")
    async def user_slash(self, ctx, member: Member):
        """
        Reset a member's Wins, Losses, MMR and MVP votes back to 0.
        """
        await self.user(ctx, member)

def setup(bot):
    bot.add_cog(Admin(bot))