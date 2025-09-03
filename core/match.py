from pymongo import MongoClient
import asyncio
import itertools
import json
import random
import re
import traceback
import uuid
from datetime import datetime, timedelta

import async_timeout
import websockets
from disnake import ButtonStyle, Color, Embed, PermissionOverwrite, SelectOption, ui
from disnake.ext import tasks
from trueskill import Rating, quality

from core.buttons import ConfirmationButtons
from core.embeds import error, success
from core.selectmenus import SelectMenuDeploy

LOL_LABELS = ["Top", "Jungle", "Mid", "ADC", "Support"]
VALORANT_LABELS = ["Controller", "Initiator", "Sentinel", "Duelist", "Flex"]
MARVEL_LABELS = ["Gracz 1", "Gracz 2", "Gracz 3", "Gracz 4", "Gracz 5", "Gracz 6"]
OVERWATCH_LABELS = ["Tank", "DPS 1", "DPS 2", "Support 1", "Support 2"]
SPECTRE_LABELS = ["Gracz 1", "Gracz 2", "Gracz 3"]
OTHER_LABELS = ["Role 1", "Role 2", "Role 3", "Role 4", "Role 5"]

async def create_indexes(bot):
    await bot.execute("game_members", "INDEX", {"game_id": 1})
    await bot.execute("game_members", "INDEX", {"author_id": 1})
    await bot.execute("games", "INDEX", {"game_id": 1})
    await bot.execute("ready_ups", "INDEX", {"game_id": 1})
    await bot.execute("mmr_ratings", "INDEX", [("user_id", 1), ("guild_id", 1), ("game", 1)])

async def start_queue(bot, channel, game, author=None, existing_msg=None, game_id=None):
    def region_icon(region, game):
        if game == "lol":
            if region == "euw":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853028175934/OW_Europe.png"
            elif region == "eune":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853028175934/OW_Europe.png"
            elif region == "br":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
            elif region == "la":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
            elif region == "jp":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
            elif region == "las":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852579373136/OW_Americas.png"
            elif region == "tr":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
            elif region == "oce":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
            elif region == "ru":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853233684581/VAL_AP.png"
            else:
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444852369670214/VAL_NA.png"
        elif game == "valorant":
            if region == "ap":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957848161591387/VAL_AP.png"
            elif region == "br":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957848409067661/VAL_BR.png"
            elif region == "kr":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957848660713494/VAL_KR.png"
            elif region == "latam":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957848899801129/VAL_LATAM.png"
            elif region == "na":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957849130467408/VAL_NA.png"
            else:
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1075444853028175934/OW_Europe.png"
        elif game in ["overwatch", "spectre", "marvel"]:
            if region == "americas":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957898329673728/OW_Americas.png"
            elif region == "asia":
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957898598101022/OW_Asia.png?width=572&height=572"
            else:
                icon_url = "https://media.discordapp.net/attachments/1046664511324692520/1077957898963013814/OW_Europe.png"
        else:
            icon_url = ""
        return icon_url

    def banner_icon(game):
        if game == "lol":
            return "https://cdn.discordapp.com/attachments/328696263568654337/1068133100451803197/image.png"
        elif game == "valorant":
            return "https://media.discordapp.net/attachments/1046664511324692520/1077958380964036689/image.png"
        elif game == "overwatch":
            return "https://i.ibb.co/rb3Rr9R/images.jpg"
        elif game == "spectre":
            return "https://i.ibb.co/RjVpqh2/inhousebanner-7.jpg"
        elif game == "marvel":
            return "https://i.ibb.co/sJ6h8j1w/9721935.gif"
        else:
            return "https://media.discordapp.net/attachments/328696263568654337/1067908043624423497/image.png?width=1386&height=527"

    def get_title(game):
        if game == "lol":
            return "Match Overview - SR Tournament Draft"
        elif game == "valorant":
            return "Match Overview - Valorant Competitive"
        elif game == "overwatch":
            return "MIXY - Overwatch 2"
        elif game == "spectre":
            return "MECZ - Spectre Divide"
        elif game == "marvel":
            return "MIXY - Marvel Rivals"
        else:
            return "Match Overview"

    data = await bot.fetchrow("queuechannels", {"channel_id": channel.id})
    if not data:
        try:
            return await channel.send(embed=error(f"{channel.mention} is not setup as the queue channel..."))
        except:
            if author:
                return await author.send(embed=error(f"Could not send queue in {channel.mention}..."))

    testmode = await bot.check_testmode(channel.guild.id)
    title = "1v1 Test Mode" if testmode else get_title(game)
    
    embed = Embed(title=title, color=Color.red())
    st_pref = await bot.fetchrow("switch_team_preference", {"guild_id": channel.guild.id})
    
    if not st_pref:
        if existing_msg:
            game_members = await bot.fetch("game_members", {"game_id": game_id})
            slot1 = ""
            slot2 = ""
            for i, member in enumerate(game_members):
                if i in range(0, 5):
                    slot1 += f"<@{member['author_id']}> - `{member['role'].capitalize()}`\n"
                else:
                    slot2 += f"<@{member['author_id']}> - `{member['role'].capitalize()}`\n"
        else:
            slot1 = "Nie ma jeszcze członków"
            slot2 = "Nie ma jeszcze członków"
        embed.add_field(name="Sloty 1", value=slot1)
        embed.add_field(name="Sloty 2", value=slot2)
        sbmm = True
    else:
        if existing_msg:
            game_members = await bot.fetch("game_members", {"game_id": game_id})
            blue_value = ""
            red_value = ""
            for member in game_members:
                if member['team'] == "blue":
                    blue_value += f"<@{member['author_id']}> - `{member['role'].capitalize()}`\n"
                else:
                    red_value += f"<@{member['author_id']}> - `{member['role'].capitalize()}`\n"
        else:
            blue_value = "Brak członków"
            red_value = "Brak członków"
        embed.add_field(name="🔵 Blue", value=blue_value)
        embed.add_field(name="🔴 Red", value=red_value)
        sbmm = False
    
    if channel.guild.id == 1071099639333404762:
        embed.set_image(url="https://i.ibb.co/sJ6h8j1w/9721935.gif")
    else:
        banner = banner_icon(game)
        if banner:
            embed.set_image(url=banner)
    
    with open('assets/tips.txt', 'r') as f:
        tips = f.readlines()
        tip = random.choice(tips)
    
    footer_game_id = game_id if existing_msg else str(uuid.uuid4()).split("-")[0]
    embed.set_footer(text="🎮 " + footer_game_id + '\n' + "💡 " + tip)
    
    if not data.get('region'):
        data['region'] = 'na'
    icon_url = region_icon(data['region'], game)
    if icon_url:
        embed.set_author(name=f"{data['region'].upper()} Queue", icon_url=icon_url)
    
    duo_pref = await bot.fetchrow("duo_queue_preference", {"guild_id": channel.guild.id})
    duo = bool(duo_pref)
    
    try:
        if existing_msg:
            await existing_msg.edit(embed=embed, view=Queue(bot, sbmm, duo, game, testmode), content="")
        else:
            await channel.send(embed=embed, view=Queue(bot, sbmm, duo, game, testmode))
    except:
        if author:
            await author.send(embed=error(f"Could not send queue in {channel.mention}, please check my permissions."))

class SpectateButton(ui.View):
    def __init__(self, bot, game_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id

    async def process_button(self, button, inter):
        await inter.response.defer()
        team = "Red" if "Red" in button.label else "Blue"
        data = await self.bot.fetchrow("games", {"game_id": self.game_id})
        if not data:
            return await inter.send(embed=error("Ten mecz się skończył."), ephemeral=True)

        members_data = await self.bot.fetch("game_members", {"game_id": self.game_id})
        for member in members_data:
            if member['author_id'] == inter.author.id:
                return await inter.send(embed=error("Nie możesz obserwować, ponieważ jesteś częścią gry."), ephemeral=True)

        await inter.send(embed=success(f"Teraz obserwujesz {team} team!"), ephemeral=True)
        lobby = self.bot.get_channel(data['lobby_id'])
        voice = self.bot.get_channel(data['voice_red_id'] if team == "Red" else data['voice_blue_id'])

        lobby_overwrites = lobby.overwrites
        lobby_overwrites.update({inter.author: PermissionOverwrite(send_messages=True)})
        voice_overwrites = voice.overwrites
        voice_overwrites.update({inter.author: PermissionOverwrite(send_messages=True, connect=True, speak=False)})

        await lobby.edit(overwrites=lobby_overwrites)
        await voice.edit(overwrites=voice_overwrites)

    @ui.button(label="Spectate Red", style=ButtonStyle.red, custom_id="lol-specred")
    async def spec_red(self, button, inter):
        await self.process_button(button, inter)

    @ui.button(label="Spectate Blue", style=ButtonStyle.blurple, custom_id="lol-specblue")
    async def spec_blue(self, button, inter):
        await self.process_button(button, inter)

class RoleButtons(ui.Button):
    def __init__(self, bot, label, custom_id, disabled=False):
        super().__init__(label=label, style=ButtonStyle.green, custom_id=custom_id, disabled=disabled)
        self.bot = bot
        self.cooldown = None
    
    async def in_ongoing_game(self, inter) -> bool:
        data = await self.bot.fetch("games", {"game_id": {"$exists": True}})
        for entry in data:
            user_roles = [x.id for x in inter.author.roles]
            if entry['red_role_id'] in user_roles or entry['blue_role_id'] in user_roles:
                return True
        return False

    async def add_participant(self, inter, button, view) -> None:
        preference = await self.bot.fetchrow("queue_preference", {"guild_id": inter.guild.id})
        preference = preference['preference'] if preference else 1
        
        if preference == 2:
            in_other_games = await self.bot.fetch("game_members", {"author_id": inter.author.id, "game_id": {"$ne": view.game_id}})
            if in_other_games:
                return await inter.send(embed=error("Nie możesz należeć do wielu kolejek."), ephemeral=True)

        label = button.label.lower()
        team = "blue"
        data = await self.bot.fetchrow("game_members", {"role": label, "game_id": view.game_id})
        if data:
            if data['team'] == "blue":
                team = "red"
            view.disabled.append(label)

        try:
            await self.bot.execute("game_members", "INSERT", {
                "author_id": inter.author.id,
                "role": label,
                "team": team,
                "game_id": view.game_id,
                "queue_id": inter.message.id,
                "channel_id": inter.channel.id,
                "guild_id": inter.guild.id
            })
        except Exception as e:
            print(f"MongoDB error: {e}")
            await inter.send(embed=error("Database error occurred"), ephemeral=True)
            return

        embed = await view.gen_embed(inter.message, view.game_id)
        await inter.message.edit(view=view, embed=embed, attachments=[])
        await inter.send(embed=success(f"Zostałeś przydzielony jako **{label.capitalize()}**."), ephemeral=True)

    async def disable_buttons(self, inter, view):
        for label in view.disabled:
            for btn in view.children:
                if btn.label.lower() == label:
                    btn.disabled = True
                    btn.style = ButtonStyle.gray
        await inter.edit_original_message(view=view)

    async def callback(self, inter):
        await inter.response.defer()
        view: Queue = self.view
        view.check_gameid(inter)
        
        if await self.in_ongoing_game(inter):
            return await inter.send(embed=error("Jesteś już w toczącej się grze."), ephemeral=True)
        
        game_members = await self.bot.fetch("game_members", {"game_id": view.game_id})
        for member in game_members:
            data = await self.bot.fetch("game_members", {"role": member['role'], "game_id": view.game_id})
            if len(data) == 2 and member['role'] not in view.disabled:
                view.disabled.append(member['role'])
        
        if self.label.lower() in view.disabled:
            return await inter.send(embed=error("Ta rola została zajęta, wybierz inną."), ephemeral=True)

        if await view.has_participated(inter, view.game_id):
            return await inter.send(embed=error("Jesteś już uczestnikiem tej gry."), ephemeral=True)

        await self.add_participant(inter, self, view)
        await self.disable_buttons(inter, view)
        await view.check_end(inter)

class LeaveButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(label="Opuść kolejkę", style=ButtonStyle.red, custom_id=f"{game}-queue:leave")

    async def callback(self, inter):
        view: Queue = self.view
        view.check_gameid(inter)
        if await view.has_participated(inter, view.game_id):
            try:
                await self.bot.execute("game_members", "DELETE", None, {"author_id": inter.author.id, "game_id": view.game_id})
                await self.bot.execute("duo_queues", "DELETE", None, {"$or": [{"user1_id": inter.author.id, "game_id": view.game_id}, {"user2_id": inter.author.id, "game_id": view.game_id}]})
            except Exception as e:
                print(f"MongoDB error: {e}")
                await inter.send(embed=error("Database error occurred"), ephemeral=True)
                return

            embed = await view.gen_embed(inter.message, view.game_id)
            for button in view.children:
                if button.label in ["Opuść Kolejkę", "Zmień Drużyne", "Duo"]:
                    continue
                data = await self.bot.fetch("game_members", {"game_id": view.game_id, "role": button.label.lower()})
                if len(data) < 2:
                    if button.disabled:
                        view.disabled.remove(button.label.lower())
                        button.disabled = False
                        button.style = ButtonStyle.green

            await inter.message.edit(view=view, embed=embed)
            await inter.send(embed=success("Zostałeś usunięty z listy uczestników."), ephemeral=True)
        else:
            await inter.send(embed=error("Nie jesteś uczestnikiem tej gry."), ephemeral=True)

class SwitchTeamButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(label="Zmień Drużyne", style=ButtonStyle.blurple, custom_id=f"{game}-queue:switch")
    
    async def callback(self, inter):
        await inter.response.defer()
        view: Queue = self.view
        view.check_gameid(inter)
        data = await self.bot.fetchrow("game_members", {"author_id": inter.author.id, "game_id": view.game_id})
        if data:
            check = await self.bot.fetchrow("game_members", {"role": data['role'], "game_id": view.game_id, "author_id": {"$ne": inter.author.id}})
            if check:
                return await inter.send("Drugie stanowisko w zespole na tę rolę jest już zajęte.", ephemeral=True)

            team = "red" if data['team'] == "blue" else "blue"
            try:
                await self.bot.execute("game_members", "UPDATE", {"team": team}, {"game_id": view.game_id, "author_id": inter.author.id})
            except Exception as e:
                print(f"MongoDB error: {e}")
                await inter.send(embed=error("Database error occurred"), ephemeral=True)
                return

            await inter.edit_original_message(embed=await view.gen_embed(inter.message, view.game_id))
            await inter.send(f"Zostałeś przydzielony **{team.capitalize()} zespół**.", ephemeral=True)
        else:
            await inter.send(embed=error("You are not a part of this game."), ephemeral=True)

class DuoButton(ui.Button):
    def __init__(self, bot, game):
        self.bot = bot
        super().__init__(label="Duo", style=ButtonStyle.blurple, custom_id=f"{game}-queue:duo")

    async def callback(self, inter):
        await inter.response.defer()
        duo_pref = await self.bot.fetchrow("duo_queue_preference", {"guild_id": inter.guild.id})
        if not duo_pref:
            return await inter.send(embed=error("Duo queue is not enabled. Please ask an admin to run `/admin duo_queue Enabled`"), ephemeral=True)

        view = self.view
        if isinstance(view, Queue):
            view.check_gameid(inter)

        queue_check = await self.bot.fetchrow("game_members", {"author_id": inter.author.id, "game_id": view.game_id})
        if not queue_check:
            return await inter.send(embed=error("Nie jesteś częścią tej kolejki :C"), ephemeral=True)
        
        queue_members = await self.bot.fetch("game_members", {"game_id": view.game_id})
        options = []
        for member_data in queue_members:
            duos = await self.bot.fetch("duo_queues", {"game_id": view.game_id})
            member = inter.guild.get_member(member_data['author_id'])
            if member.id == inter.author.id or member_data['role'] == queue_check['role']:
                continue
            check = any(member.id in [duo['user1_id'], duo['user2_id']] for duo in duos)
            if check:
                continue
            options.append(SelectOption(label=member.display_name, value=str(member.id)))

        if not options:
            return await inter.send(embed=error("Nie udało się znaleźć dla Ciebie dostępnych członków duetu."), ephemeral=True)

        async def Function(select_inter, vals, *args):
            con_view = ConfirmationButtons(inter.author.id)
            m = inter.guild.get_member(int(vals[0]))
            await inter.send(f"Czy na pewno chcesz stworzyć duet z {m.display_name}?", view=con_view, ephemeral=True)
            await con_view.wait()
            if con_view.value:
                con_view = ConfirmationButtons(m.id)
                try:
                    await m.send(embed=Embed(
                        title="👥 Prośba o duet",
                        description=f"**{inter.author.display_name}** wysłał Ci zaproszenie do gry w duecie **{args[0]}** in {inter.channel.mention}. Akceptujesz?",
                        color=Color.red()
                    ), view=con_view)
                except:
                    return await inter.send(embed=success(f"Nie można wysłać żądania kolejki duo do {m.display_name}. Ich czaty mogą być wyłączone dla bota."), ephemeral=True)
                await inter.send(embed=success(f"Wysłano zapytanie kolejki Duo do {m.display_name}"), ephemeral=True)
                await con_view.wait()
                if con_view.value:
                    user_duos = await self.bot.fetch("duo_queues", {"game_id": view.game_id})
                    if any(int(vals[0]) in [duo['user1_id'], duo['user2_id']] for duo in user_duos):
                        return await m.send(embed=error("Jesteś już w duecie."))
                    try:
                        await self.bot.execute("duo_queues", "INSERT", {
                            "guild_id": inter.guild.id,
                            "user1_id": inter.author.id,
                            "user2_id": int(vals[0]),
                            "game_id": args[0],
                            "created_at": datetime.now()
                        })
                    except Exception as e:
                        print(f"MongoDB error: {e}")
                        await inter.send(embed=error("Database error occurred"), ephemeral=True)
                        return

                    if isinstance(self, Queue):
                        embed = await self.gen_embed(inter.message)
                    else:
                        ready_ups = await self.bot.fetch("ready_ups", {"game_id": view.game_id})
                        ready_ups = [x['user_id'] for x in ready_ups]
                        st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": inter.guild.id})
                        if st_pref:
                            embed = await ReadyButton(self.bot, view.game, view.game_id, inter.message).team_embed(ready_ups)
                        else:
                            embed = await ReadyButton(self.bot, view.game, view.game_id, inter.message).anonymous_team_embed(ready_ups)
                    await inter.message.edit(embed=embed, attachments=[]) 
                    await m.send(embed=success(f"Udało Ci się nawiązać duet z {inter.author.display_name}"))

        await inter.send(content="Wybierz członka, z którym chcesz stworzyć duet.", view=SelectMenuDeploy(self.bot, inter.author.id, options, 1, 1, Function, view.game_id), ephemeral=True)

class ReadyButton(ui.Button):
    def __init__(self, bot, game, game_id, msg=None):
        self.bot = bot
        self.game = game
        self.game_id = game_id
        self.time_of_execution = datetime.now()
        self.data = None
        self.msg = msg
        super().__init__(label="Gotowy!", style=ButtonStyle.green, custom_id=f"{game}-queue:readyup")
        self.disable_button.start()
    
    async def anonymous_team_embed(self, ready_ups):
        embed = self.msg.embeds[0]
        embed.clear_fields()
        embed.description = "WAŻNE: To nie są zespoły finałowe (sprawdź kanał #lobby-xyz)"
        duos = await self.bot.fetch("duo_queues", {"game_id": self.game_id})
        in_duo = {}
        for i, duo in enumerate(duos):
            duo_emojis = [":one:", ":two:", ":three:", ":four:"]
            in_duo.update({duo['user1_id']: duo_emojis[i]})
            in_duo.update({duo['user2_id']: duo_emojis[i]})
        
        team_data = await self.bot.fetch("game_members", {"game_id": self.game_id})
        value1 = ""
        value2 = ""
        for i, team in enumerate(team_data):
            value = ""
            if team['author_id'] in ready_ups:
                value += "✅"
            else:
                value += "❌"
            if team['author_id'] in in_duo:
                value += f"{in_duo[team['author_id']]} "
            value += f"<@{team['author_id']}> - `{team['role'].capitalize()}` \n"
            if i in range(0, 5):
                value1 += value
            else:
                value2 += value

        embed.add_field(name="👥 Uczestnicy", value=value1 or "Brak członków")
        embed.add_field(name="👥 Uczestnicy", value=value2 or "Brak członków")
        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips) 
        embed.set_footer(text="🎮 " + self.game_id + '\n' + "💡 " + tip)
        return embed

    async def team_embed(self, ready_ups):
        embed = self.msg.embeds[0]
        embed.clear_fields()
        embed.description = ""
        duos = await self.bot.fetch("duo_queues", {"game_id": self.game_id})
        in_duo = []
        for duo in duos:
            in_duo.extend([duo['user1_id'], duo['user2_id']])
        duo_usage = 0
        duo_emoji = ":one:"

        for team in ["blue", "red"]:
            team_data = await self.bot.fetch("game_members", {"game_id": self.game_id, "team": team})
            emoji = "🔴" if team == "red" else "🔵"
            name = f"{emoji} {team.capitalize()}"
            value = ""
            for data in team_data:
                if data['author_id'] in ready_ups:
                    value += "✅ "
                else:
                    value += "❌ "
                if data['author_id'] in in_duo:
                    value += f"{duo_emoji} "
                    duo_usage += 1
                    if not duo_usage % 2:
                        if duo_usage / 2 == 1:
                            duo_emoji = ":two:"
                        elif duo_usage / 2 == 2:
                            duo_emoji = ":three:"
                        elif duo_usage / 2 == 3:
                            duo_emoji = ":four:"
                        else:
                            duo_emoji = ":five:"
                value += f"<@{data['author_id']}> - `{data['role'].capitalize()}`\n"
            embed.add_field(name=name, value=value or "Brak członków")

        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips) 
        embed.set_footer(text="🎮 " + self.game_id + '\n' + "💡 " + tip)
        return embed

    async def lol_lobby(self, inter, lobby_channel):
        response = None
        async with websockets.connect("wss://draftlol.dawe.gg/") as websocket:
            data = {"type": "createroom", "blueName": "In-House Queue Blue", "redName": "In-House Queue Red", "disabledTurns": [], "disabledChamps": [], "timePerPick": "30", "timePerBan": "30"}
            await websocket.send(json.dumps(data))
            try:
                async with async_timeout.timeout(10):
                    result = await websocket.recv()
                    if result:
                        data = json.loads(result)
                        response = ("🔵 https://draftlol.dawe.gg/" + data["roomId"] +"/" +data["bluePassword"], "🔴 https://draftlol.dawe.gg/" + data["roomId"] +"/" +data["redPassword"], "\n**Spectators:** https://draftlol.dawe.gg/" + data["roomId"])
            except asyncio.TimeoutError:
                pass
        
        if response:
            await lobby_channel.send(embed=Embed(title="League of Legends Draft", description="\n".join(response), color=Color.blurple()))
        else:
            await lobby_channel.send(embed=error("Draftlol is down, could not retrieve links."))

        region = (await self.bot.fetchrow("queuechannels", {"channel_id": inter.channel.id}))['region'] or 'na'
        teams = {'blue': '', 'red': ''}
        for team in teams:
            url = f'https://www.op.gg/multisearch/{region}?summoners='
            data = await self.bot.fetch("game_members", {"game_id": self.game_id, "team": team})
            nicknames = []
            for entry in data:
                ign = await self.bot.fetchrow("igns", {"guild_id": inter.guild.id, "user_id": entry['author_id'], "game": 'lol'})
                if ign:
                    nicknames.append(ign['ign'].replace(' ', '%20'))
                else:
                    member = lobby_channel.guild.get_member(entry['author_id'])
                    nick = member.nick or member.name
                    nick = re.sub(r"ign(:)?\s*", "", nick, flags=re.IGNORECASE)
                    nicknames.append(nick.replace(' ', '%20'))
            url += "%2C".join(nicknames)
            teams[team] = url
        
        await lobby_channel.send(embed=Embed(
            title="🔗 Multi OP.GG",
            description=f"🔵{teams['blue']}\n🔴{teams['red']} \n \n :warning: If the OP.GG  **region** is incorrect, update your queue channel region with `/setregion`",
            color=Color.blurple()
        ))

    async def valorant_lobby(self, lobby_channel):
        map_dict = random.choice(self.bot.valorant_maps)
        map_name = list(map_dict.keys())[0]
        map_link = map_dict[map_name]
        embed = Embed(title="Game Map (Optional)", description=f"Set the game map to **{map_name}**.", color=Color.red())
        embed.set_image(url=map_link)
        await lobby_channel.send(embed=embed)

        options = [SelectOption(label=label, value=label.lower()) for label in VALORANT_LABELS if label != "Flex"]

        async def Function(inter, val, *args):
            try:
                await self.bot.execute("game_members", "UPDATE", {"role": f"flex - {val[0]}"}, {"author_id": inter.author.id, "game_id": self.game_id})
            except Exception as e:
                print(f"MongoDB error: {e}")
                await inter.send(embed=error("Database error occurred"), ephemeral=True)
                return
            await inter.send(embed=success(f"You've been given {val[0].capitalize()} successfully."), ephemeral=True)
            await inter.delete_original_message()
        
        flex_roles = await self.bot.fetch("game_members", {"game_id": self.game_id, "role": "flex"})
        for holder in flex_roles:
            view = SelectMenuDeploy(self.bot, holder['author_id'], options, 1, 1, Function)
            await lobby_channel.send(content=f"<@{holder['author_id']}> select the role you wish to play.", view=view)

    async def overwatch_lobby(self, lobby_channel):
        gamemode_dict = random.choice(self.bot.overwatch)
        gamemode_name = list(gamemode_dict.keys())[0]
        gamemode_maps_Dict = gamemode_dict[gamemode_name]
        map_dict = random.choice(gamemode_maps_Dict)
        map_name = list(map_dict.keys())[0]
        map_link = map_dict[map_name]
        embed = Embed(title="Ustawienia gry (opcjonalne)", description=f"Tryb gry: **{gamemode_name}** \nMapa gry: **{map_name}**", color=Color.red())
        embed.set_image(url=map_link)
        await lobby_channel.send(embed=embed)
        
    async def spectre_lobby(self, lobby_channel):
        map_dict = random.choice(self.bot.spectre_maps)
        map_name = list(map_dict.keys())[0]
        map_link = map_dict[map_name]
        embed = Embed(title="Mapa (Opcjonalnie)", description=f"Wybierz mape **{map_name}**.", color=Color.red())
        embed.set_image(url=map_link)
        await lobby_channel.send(embed=embed)
        
    async def marvel_lobby(self, lobby_channel):
        gamemode_dict = random.choice(self.bot.marvel)
        gamemode_name = list(gamemode_dict.keys())[0]
        gamemode_maps_Dict = gamemode_dict[gamemode_name]
        map_dict = random.choice(gamemode_maps_Dict)
        map_name = list(map_dict.keys())[0]
        map_link = map_dict[map_name]
        embed = Embed(title="Ustawienia gry (opcjonalne)", description=f"Tryb gry: **{gamemode_name}** \nMapa gry: **{map_name}**", color=Color.red())
        embed.set_image(url=map_link)
        await lobby_channel.send(embed=embed)

    async def check_members(self, msg):
        members = await self.bot.fetch("game_members", {"game_id": self.game_id})
        required_members = 2 if await self.bot.check_testmode(msg.guild.id) else (6 if self.game == "spectre" else 12 if self.game == "marvel" else 10)
        if len(members) != required_members:
            self.disable_button.stop()
            await start_queue(self.bot, msg.channel, self.game, None, msg, self.game_id)

    @tasks.loop(seconds=1)
    async def disable_button(self):
        await self.bot.wait_until_ready()
        if self.msg:
            await self.check_members(self.msg)
            msg = self.bot.get_message(self.msg.id)
            if not msg:
                msg = await self.msg.channel.fetch_message(self.msg.id)
                if msg:
                    self.msg = msg
            else:
                self.msg = msg

            if not self.msg.components[0].children[0].label == "Gotowy!":
                self.disable_button.stop()
                return

        if (datetime.now() - self.time_of_execution).seconds >= 300:
            if self.msg:
                ready_ups = await self.bot.fetch("ready_ups", {"game_id": self.game_id})
                ready_ups = [x['user_id'] for x in ready_ups]
                game_members = [member['author_id'] for member in self.data]
                players_removed = []

                for user_id in game_members:
                    if user_id not in ready_ups:
                        try:
                            await self.bot.execute("game_members", "DELETE", None, {"author_id": user_id, "game_id": self.game_id})
                            await self.bot.execute("duo_queues", "DELETE", None, {"$or": [{"game_id": self.game_id, "user1_id": user_id}, {"game_id": self.game_id, "user2_id": user_id}]})
                        except Exception as e:
                            print(f"MongoDB error: {e}")
                            continue
                        players_removed.append(user_id)
                        user = self.bot.get_user(user_id)
                        await user.send(embed=Embed(description=f"Zostałeś usunięty z [queue]({self.msg.jump_url}) za nie bycie gotowym na czas.", color=Color.red()))

                try:
                    await self.bot.execute("ready_ups", "DELETE", None, {"game_id": self.game_id})
                except Exception as e:
                    print(f"MongoDB error: {e}")

                st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": self.msg.guild.id})
                sbmm = not bool(st_pref)
                duo_pref = await self.bot.fetchrow("duo_queue_preference", {"guild_id": self.msg.guild.id})
                duo = bool(duo_pref)
                test_mode = await self.bot.check_testmode(self.msg.guild.id)
                await self.msg.edit(
                    embed=await Queue.gen_embed(self, self.msg, self.game_id, test_mode),
                    view=Queue(self.bot, sbmm, duo, self.game),
                    content="Nie wszyscy zawodnicy byli gotowi, kolejka została zwolniona."
                )
                if players_removed:
                    await self.msg.channel.send(
                        content=", ".join(f"<@{x}>" for x in players_removed),
                        embed=Embed(description="Wspomniani gracze zostali usunięci z kolejki za nieprzygotowanie się na czas.", color=Color.blurple()),
                        delete_after=60.0
                    )
                self.disable_button.stop()
            else:
                self.time_of_execution = datetime.now()

    async def callback(self, inter):
        if not inter.response.is_done():
            await inter.response.defer()

        if not self.msg:
            self.msg = inter.message

        if not self.data:
            self.data = await self.bot.fetch("game_members", {"game_id": self.game_id})
        
        await self.check_members(inter.message)
        game_members = [member['author_id'] for member in self.data]
        ready_ups = await self.bot.fetch("ready_ups", {"game_id": self.game_id})
        ready_ups = [x['user_id'] for x in ready_ups]

        if inter.author.id in game_members:
            if inter.author.id in ready_ups:
                await inter.send(embed=success("Jesteś gotowy, wiemy."), ephemeral=True)
                return

            try:
                await self.bot.execute("ready_ups", "INSERT", {"game_id": self.game_id, "user_id": inter.author.id, "timestamp": datetime.now()})
            except Exception as e:
                print(f"MongoDB error: {e}")
                await inter.send(embed=error("Database error occurred"), ephemeral=True)
                return

            ready_ups.append(inter.author.id)
            st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": inter.guild.id})
            embed = await self.team_embed(ready_ups) if st_pref else await self.anonymous_team_embed(ready_ups)
            await inter.message.edit(
                content=f"{len(ready_ups)}/{10 if not await self.bot.check_testmode(inter.guild.id) else 2} Graczy jest gotowych!\nPrzygotuj się przed <t:{int(datetime.timestamp((self.time_of_execution + timedelta(seconds=290))))}:t>",
                embed=embed
            )

            required_readyups = 2 if await self.bot.check_testmode(inter.guild.id) else (6 if self.game == "spectre" else 12 if self.game == "marvel" else 10)
            if len(ready_ups) == required_readyups:
                if not st_pref:
                    member_data = await self.bot.fetch("game_members", {"game_id": self.game_id})
                    labels = {
                        'lol': LOL_LABELS,
                        'valorant': VALORANT_LABELS,
                        'overwatch': OVERWATCH_LABELS,
                        'spectre': SPECTRE_LABELS,
                        'marvel': MARVEL_LABELS
                    }.get(self.game, OTHER_LABELS)
                    
                    roles_occupation = {
                        labels[0].upper(): [],
                        labels[1].upper(): [],
                        labels[2].upper(): [],
                        labels[3].upper(): [],
                        labels[4].upper(): []
                    } if not await self.bot.check_testmode(inter.guild.id) else {
                        labels[0].upper(): [{'user_id': 890, 'rating': Rating()}, {'user_id': 3543, 'rating': Rating()}],
                        labels[1].upper(): [{'user_id': 709, 'rating': Rating()}, {'user_id': 901, 'rating': Rating()}],
                        labels[2].upper(): [{'user_id': 789, 'rating': Rating()}, {'user_id': 981, 'rating': Rating()}],
                        labels[3].upper(): [{'user_id': 234, 'rating': Rating()}, {'user_id': 567, 'rating': Rating()}],
                        labels[4].upper(): []
                    }

                    for data in member_data:
                        member_rating = await self.bot.fetchrow("mmr_ratings", {"user_id": data['author_id'], "guild_id": inter.guild.id, "game": self.game})
                        rating = Rating(mu=float(member_rating['mu']), sigma=float(member_rating['sigma'])) if member_rating else Rating()
                        if not member_rating:
                            await self.bot.execute("mmr_ratings", "INSERT", {
                                "guild_id": inter.guild.id,
                                "user_id": data['author_id'],
                                "mu": rating.mu,
                                "sigma": rating.sigma,
                                "counter": 0,
                                "game": self.game
                            })
                        roles_occupation[data['role'].upper()].append({'user_id': data['author_id'], 'rating': rating})

                    all_occupations = [*roles_occupation.values()]
                    unique_combinations = list(itertools.product(*all_occupations))
                    team_data = []
                    qualities = []
                    for pair in unique_combinations:
                        players_in_pair = [x['user_id'] for x in list(pair)]
                        t2 = []
                        for x in roles_occupation:
                            for val in roles_occupation[x]:
                                if val['user_id'] not in players_in_pair:
                                    t2.append(val)
                        duo = await self.bot.fetch("duo_queues", {"game_id": self.game_id})
                        check = True
                        for duo_data in duo:
                            user1 = duo_data['user1_id']
                            user2 = duo_data['user2_id']
                            if not ((user1 in players_in_pair and user2 in players_in_pair) or (user1 in [x['user_id'] for x in t2] and user2 in [x['user_id'] for x in t2])):
                                check = False
                        if not check:
                            continue
                        qua = quality([[x['rating'] for x in list(pair)], [x['rating'] for x in t2]])
                        qualities.append(qua)
                        team_data.append({'quality': qua, 'teams': [list(pair), t2]})

                    closet_quality = qualities[min(range(len(qualities)), key=lambda i: abs(qualities[i] - 50))]
                    for entry in team_data:
                        if entry['quality'] == closet_quality:
                            final_teams = entry['teams']
                    
                    for i, team_entries in enumerate(final_teams):
                        team = 'blue' if i else 'red'
                        for entry in team_entries:
                            await self.bot.execute("game_members", "UPDATE", {"team": team}, {"author_id": entry['user_id'], "game_id": self.game_id})
                    self.data = await self.bot.fetch("game_members", {"game_id": self.game_id})
                
                preference = await self.bot.fetchrow("queue_preference", {"guild_id": inter.guild.id})
                preference = preference['preference'] if preference else 1

                if preference == 1:
                    await self.bot.execute("game_members", "DELETE", None, {"author_id": {"$in": game_members}, "game_id": {"$ne": self.game_id}})

                await self.bot.execute("ready_ups", "DELETE", None, {"game_id": self.game_id})

                try:
                    red_role = await inter.guild.create_role(name=f"Red: {self.game_id}")
                    blue_role = await inter.guild.create_role(name=f"Blue: {self.game_id}")
                    overwrites_red = {
                        inter.guild.default_role: PermissionOverwrite(connect=False),
                        red_role: PermissionOverwrite(connect=True),
                        self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True, connect=True)
                    }
                    overwrites_blue = {
                        inter.guild.default_role: PermissionOverwrite(connect=False),
                        blue_role: PermissionOverwrite(connect=True),
                        self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True, connect=True)
                    }
                    mutual_overwrites = {
                        inter.guild.default_role: PermissionOverwrite(send_messages=False),
                        red_role: PermissionOverwrite(send_messages=True),
                        blue_role: PermissionOverwrite(send_messages=True),
                        self.bot.user: PermissionOverwrite(send_messages=True, manage_channels=True)
                    }
                    game_category_id = await self.bot.fetchrow("game_categories", {"guild_id": inter.guild.id, "game": self.game})
                    game_category = self.bot.get_channel(game_category_id['category_id']) if game_category_id else await inter.guild.create_category(name=f"Mecz: {self.game_id}", overwrites=mutual_overwrites)
                    game_lobby = await game_category.create_text_channel(f"Lobby: {self.game_id}", overwrites=mutual_overwrites)
                    voice_channel_red = await game_category.create_voice_channel(f"Red: {self.game_id}", overwrites=overwrites_red)
                    voice_channel_blue = await game_category.create_voice_channel(f"Blue: {self.game_id}", overwrites=overwrites_blue)
                except:
                    await inter.send(embed=error("Nie można utworzyć kanałów/ról. Prosimy o kontakt z administratorami."))
                    print(traceback.format_exc())
                    return

                await inter.message.edit(content="Gra jest obecnie w toku!", view=SpectateButton(self.bot, self.game_id))
                for entry in self.data:
                    member = inter.guild.get_member(entry['author_id'])
                    await member.add_roles(red_role if entry['team'] == "red" else blue_role)

                await game_lobby.send(
                    content=f"{red_role.mention} {blue_role.mention}",
                    embed=await self.team_embed(ready_ups),
                    view=SpectateButton(self.bot, self.game_id)
                )
                await game_lobby.send(embed=Embed(
                    title=":warning: Ogłoszenie",
                    description=f"Aby zakończyć grę, użyj `!win` lub `/win`.\n **6** głosów **MUSI** zostać użyte.\nTylko głosy **uczestników** sie liczą.\n \n**Opcjonalnie:** Wpisz `{self.game_id}` jako niestandardową nazwę gry i hasło.",
                    color=Color.yellow()
                ))

                try:
                    await self.bot.execute("games", "INSERT", {
                        "game_id": self.game_id,
                        "lobby_id": game_lobby.id,
                        "voice_red_id": voice_channel_red.id,
                        "voice_blue_id": voice_channel_blue.id,
                        "red_role_id": red_role.id,
                        "blue_role_id": blue_role.id,
                        "queuechannel_id": inter.channel.id,
                        "msg_id": inter.message.id,
                        "game": self.game,
                        "status": "active",
                        "created_at": datetime.now()
                    })
                except Exception as e:
                    print(f"MongoDB error: {e}")
                    await inter.send(embed=error("Database error occurred"), ephemeral=True)
                    return

                if self.game == 'lol':
                    await self.lol_lobby(inter, game_lobby)
                elif self.game == 'valorant':
                    await self.valorant_lobby(game_lobby)
                elif self.game == 'overwatch':
                    await self.overwatch_lobby(game_lobby)
                elif self.game == 'spectre':
                    await self.spectre_lobby(game_lobby)
                elif self.game == 'marvel':
                    await self.marvel_lobby(game_lobby)

                self.disable_button.cancel()
                await start_queue(self.bot, inter.channel, self.game)
        else:
            await inter.send(embed=error("Nie jesteś częścią tej gry."), ephemeral=True)

class ReadyUp(ui.View):
    def __init__(self, bot, game, game_id, duo):
        super().__init__(timeout=None)
        self.bot = bot
        self.game_id = game_id
        self.game = game
        self.add_item(ReadyButton(bot, game, game_id))
        if duo:
            self.add_item(DuoButton(bot, game))

class Queue(ui.View):
    def __init__(self, bot, sbmm, duo, game, testmode):
        super().__init__(timeout=None)
        self.bot = bot
        self.disabled = []
        self.game_id = None
        self.game = game
        self.msg = None
        labels = {
            'lol': LOL_LABELS,
            'valorant': VALORANT_LABELS,
            'overwatch': OVERWATCH_LABELS,
            'spectre': SPECTRE_LABELS,
            'marvel': MARVEL_LABELS
        }.get(game, OTHER_LABELS)

        for i, label in enumerate(labels):
            self.add_item(RoleButtons(bot, label, f"{game}-queue:{label.lower()}", testmode and i == len(labels)-1))
        
        self.add_item(LeaveButton(bot, game))
        if not sbmm:
            self.add_item(SwitchTeamButton(bot, game))
        if duo and sbmm:
            self.add_item(DuoButton(bot, game))
            self.duo = True
        else:
            self.duo = False
    
    def check_gameid(self, inter):
        if not self.game_id:
            self.game_id = inter.message.embeds[0].footer.text.split('\n')[0].replace(' ', '').replace("🎮", "")

    async def has_participated(self, inter, game_id) -> bool:
        return bool(await self.bot.fetchrow("game_members", {"author_id": inter.author.id, "game_id": game_id}))
    
    async def gen_embed(self, msg, game_id, testmode=False) -> Embed:
        embed = msg.embeds[0]
        embed.clear_fields()
        teams = ["blue", "red"]
        duo_usage = 0
        duo_emoji = ":one:"
        for index, team in enumerate(teams):
            team_data = await self.bot.fetch("game_members", {"game_id": game_id, "team": team})
            emoji = "🔴" if team == "red" else "🔵"
            name = f"{emoji} {team.capitalize()}"
            st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": msg.guild.id})
            if not st_pref:
                name = f"Slot {index+1}"
            
            value = ""
            if team_data:
                duos = await self.bot.fetch("duo_queues", {"game_id": game_id})
                in_duo = []
                for duo in duos:
                    in_duo.extend([duo['user1_id'], duo['user2_id']])
                for data in team_data:
                    if data['author_id'] in in_duo:
                        value += f"{duo_emoji} "
                        duo_usage += 1
                        if not duo_usage % 2:
                            if duo_usage / 2 == 1:
                                duo_emoji = ":two:"
                            elif duo_usage / 2 == 2:
                                duo_emoji = ":three:"
                            elif duo_usage / 2 == 3:
                                duo_emoji = ":four:"
                            else:
                                duo_emoji = ":five:"
                    value += f"<@{data['author_id']}> - `{data['role'].capitalize()}`\n"
            else:
                value = "Brak członków"
            embed.add_field(name=name, value=value)

        with open('assets/tips.txt', 'r') as f:
            tips = f.readlines()
            tip = random.choice(tips) 
        embed.set_footer(text="🎮 " + game_id + '\n' + "💡 " + tip)
        return embed

    async def check_end(self, inter) -> None:
        checks_passed = 0
        for button in self.children:
            if button.label in ["Opuść kolejkę", "Zmień Drużyne", "Duo"]:
                continue
            count = len(await self.bot.fetch("game_members", {"game_id": self.game_id, "role": button.label.lower()}))
            if count == 2:
                checks_passed += 1

        required_checks = 1 if await self.bot.check_testmode(inter.guild.id) else (3 if self.game == "spectre" else 6 if self.game == "marvel" else 5)
        if checks_passed == required_checks:
            member_data = await self.bot.fetch("game_members", {"game_id": self.game_id})
            mentions = ", ".join(f"<@{m['author_id']}>" for m in member_data)
            self.msg = inter.message
            st_pref = await self.bot.fetchrow("switch_team_preference", {"guild_id": inter.guild.id})
            embed = await ReadyButton.team_embed(self, []) if st_pref else await ReadyButton.anonymous_team_embed(self, [])
            
            await inter.edit_original_message(view=None)
            await inter.edit_original_message(
                view=ReadyUp(self.bot, self.game, self.game_id, self.duo),
                content=f"0/{10 if not await self.bot.check_testmode(inter.guild.id) else 2} Graczy jest gotowych!",
                embed=embed
            )
            embed = Embed(description=f"Znaleziono grę! Czas się przygotować!", color=Color.blurple())
            await inter.message.reply(mentions, embed=embed, delete_after=300.0)