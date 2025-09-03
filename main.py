#!/usr/bin/env/python3
import os
import topgg
from motor.motor_asyncio import AsyncIOMotorClient
from disnake import Intents
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
dbl_token = os.getenv("TOP_GG_TOKEN")

# Default roles
DEFAULT_ROLES = {
    'TOP': "🔺",
    'JUNGLE': "🟢",
    'MID': "🔷",
    'SUPPORT': "🛡️",
    'ADC': "🏹",
    'CONTROLLER': "🌫️",
    'DUELIST': "⚔️",
    'INITIATOR': "🎯",
    'SENTINEL': "🛡️",
    'TANK': "🛡️",
    'DPS': "🔫",
    'SUPPORT_OW': "💉",
    'GRACZ_1': "1️⃣",
    'GRACZ_2': "2️⃣",
    'GRACZ_3': "3️⃣",
    'GRACZ_4': "4️⃣",
    'GRACZ_5': "5️⃣",
    'GRACZ_6': "6️⃣"
}

PREFIX = "!"

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        self.db = self.mongo_client["discord_bot"]
        self.servers_config = self.db["servers_config"]

        # Initialize collections
        self.collections = [
            "queuechannels", "winner_log_channel", "points", "mmr_rating", "members_history",
            "game_member_data", "games", "mvp_voting", "mvp_points", "admin_enables",
            "igns", "queue_preference", "switch_team_preference", "duo_queue_preference",
            "testmode", "game_categories", "ready_ups", "duo_queues"
        ]

        self.role_emojis = {
            'top': DEFAULT_ROLES['TOP'],
            'jungle': DEFAULT_ROLES['JUNGLE'],
            'mid': DEFAULT_ROLES['MID'],
            'support': DEFAULT_ROLES['SUPPORT'],
            'adc': DEFAULT_ROLES['ADC'],
            'controller': DEFAULT_ROLES['CONTROLLER'],
            'duelist': DEFAULT_ROLES['DUELIST'],
            'initiator': DEFAULT_ROLES['INITIATOR'],
            'sentinel': DEFAULT_ROLES['SENTINEL'],
            'flex': "❓",
            'flex - controller': DEFAULT_ROLES['CONTROLLER'],
            'flex - duelist': DEFAULT_ROLES['DUELIST'],
            'flex - initiator': DEFAULT_ROLES['INITIATOR'],
            'flex - sentinel': DEFAULT_ROLES['SENTINEL'],
            'tank': DEFAULT_ROLES['TANK'],
            'dps 1': DEFAULT_ROLES['DPS'],
            'dps 2': DEFAULT_ROLES['DPS'],
            'support 1': DEFAULT_ROLES['SUPPORT_OW'],
            'support 2': DEFAULT_ROLES['SUPPORT_OW'],
            'gracz 1': DEFAULT_ROLES['GRACZ_1'],
            'gracz 2': DEFAULT_ROLES['GRACZ_2'],
            'gracz 3': DEFAULT_ROLES['GRACZ_3'],
            'gracz 4': DEFAULT_ROLES['GRACZ_4'],
            'gracz 5': DEFAULT_ROLES['GRACZ_5'],
            'gracz 6': DEFAULT_ROLES['GRACZ_6'],
            'role 1': "1️⃣",
            'role 2': "2️⃣",
            'role 3': "3️⃣",
            'role 4': "4️⃣",
            'role 5': "5️⃣"
        }
        self.valorant_maps = [
            {'Haven': 'https://media.valorant-api.com/maps/2bee0dc9-4ffe-519b-1cbd-7fbe763a6047/splash.png'},
            {'Split': 'https://media.valorant-api.com/maps/d960549e-485c-e861-8d71-aa9d1aed12a2/splash.png'},
            {'Ascent': 'https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/splash.png'},
            {'Icebox': 'https://media.valorant-api.com/maps/e2ad5c54-4114-a870-9641-8ea21279579a/splash.png'},
            {'Fracture': 'https://media.valorant-api.com/maps/b529448b-4d60-346e-e89e-00a4c527a405/splash.png'},
            {'Pearl': 'https://media.valorant-api.com/maps/fd267378-4d1d-484f-ff52-77821ed10dc2/splash.png'},
            {'Lotus': 'https://media.valorant-api.com/maps/2fe4ed3a-450a-948b-6d6b-e89a78e680a9/splash.png'},
            {'Bind': 'https://media.valorant-api.com/maps/2c9d57ec-4431-9c5e-2939-8f9ef6dd5cba/splash.png'},
            {'Breeze': 'https://media.valorant-api.com/maps/2fb9a4fd-47b8-4e7d-a969-74b4046ebd53/splash.png'},
        ]
        self.spectre_maps = [
            {'Korytarz': 'https://i.ibb.co/LnCp6dQ/Screenshot-375.png'},
            {'Metro': 'https://i.ibb.co/8BjQhnR/Screenshot-376.png'},
            {'Zakład': 'https://i.ibb.co/3MqCgmM/Screenshot-377.png'},
        ]
        self.overwatch = [
            {'Control': [
                {'Busan': 'https://overfast-api.tekrop.fr/static/maps/busan.jpg'},
                {'Ilios': 'https://overfast-api.tekrop.fr/static/maps/ilios.jpg'},
                {'Lijiang Tower': 'https://overfast-api.tekrop.fr/static/maps/lijiang.jpg'},
                {'Nepal': 'https://overfast-api.tekrop.fr/static/maps/nepal.jpg'},
                {'Oasis': 'https://overfast-api.tekrop.fr/static/maps/oasis.jpg'},
            ]},
            {'Escort': [
                {'Dorado': 'https://overfast-api.tekrop.fr/static/maps/dorado.jpg'},
                {'Junkertown': 'https://overfast-api.tekrop.fr/static/maps/junkertown.jpg'},
                {'Circuit Royal': 'https://overfast-api.tekrop.fr/static/maps/circuit_royal.jpg'},
                {'Rialto': 'https://overfast-api.tekrop.fr/static/maps/rialto.jpg'},
                {'Route 66': 'https://overfast-api.tekrop.fr/static/maps/route_66.jpg'},
                {'Shambali Monastery (new)': 'https://overfast-api.tekrop.fr/static/maps/shambali.jpg'},
                {'Watchpoint Gibratar': 'https://overfast-api.tekrop.fr/static/maps/gibraltar.jpg'},
            ]},
            {'Hybrid': [
                {'Blizzard World': 'https://overfast-api.tekrop.fr/static/maps/blizzard_world.jpg'},
                {'Eichenwalde': 'https://overfast-api.tekrop.fr/static/maps/eichenwalde.jpg'},
                {'King’s Row': 'https://overfast-api.tekrop.fr/static/maps/kings_row.jpg'},
                {'Midtown': 'https://overfast-api.tekrop.fr/static/maps/midtown.jpg'},
                {'Paraíso': 'https://overfast-api.tekrop.fr/static/maps/paraiso.jpg'},
                {'Numbani': 'https://overfast-api.tekrop.fr/static/maps/numbani.jpg'},
                {'Hollywood': 'https://overfast-api.tekrop.fr/static/maps/hollywood.jpg'},
            ]},
            {'Push': [
                {'Colosseo': 'https://overfast-api.tekrop.fr/static/maps/colosseo.jpg'},
                {'New Queen Street': 'https://overfast-api.tekrop.fr/static/maps/new_queen_street.jpg'},
                {'Esperança': 'https://overfast-api.tekrop.fr/static/maps/esperanca.jpg'},
            ]}
        ]
        self.marvel = [
            {'Convoy': [
                {'YGGSGARD': 'https://static.wikia.nocookie.net/marvel-rivals/images/6/66/Yggdrasill_Path.jpg'},
                {'TOKYO 2099': 'https://static.wikia.nocookie.net/marvel-rivals/images/2/2c/Spider-Islands.jpg'},
            ]},
            {'Domination': [
                {'YGGSGARD': 'https://static.wikia.nocookie.net/marvel-rivals/images/0/05/Royal_Palace.jpg'},
                {'INTERGALACTIC EMPIRE OF WAKANDA': 'https://gamingbolt.com/wp-content/uploads/2024/11/Marvel-Rivals-Intergalactic-Empire-of-Wakanda-scaled.jpg'},
                {'HYDRA CHARTERIS BASE': 'https://sm.ign.com/t/ign_in/video/m/marvel-riv/marvel-rivals-official-hydra-charteris-base-hells-heaven-map_sjyc.1280.jpg'},
            ]},
            {'Convergence': [
                {'TOKYO 2099': 'https://static.wikia.nocookie.net/marvel-rivals/images/d/da/Shin-Shibuya.jpg'},
                {'INTERGALACTIC EMPIRE OF WAKANDA': 'https://staticg.sportskeeda.com/editor/2024/12/5d0a0-17335843053779-1920.jpg'},
                {'KLYNTAR': 'https://sm.ign.com/t/ign_za/video/m/marvel-riv/marvel-rivals-official-klyntar-symbiotic-surface-map-reveal_ws13.1280.jpg'},
            ]}
        ]

    async def fetch(self, collection_name, query=None, sort=None, limit=None):
        """Fetch multiple documents from a collection."""
        if query is None:
            query = {}
        cursor = self.db[collection_name].find(query)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return [doc async for doc in cursor]

    async def fetchrow(self, collection_name, query=None):
        """Fetch a single document from a collection."""
        if query is None:
            query = {}
        return await self.db[collection_name].find_one(query)

    async def execute(self, collection_name, operation, data, query=None):
        """Execute insert, update, or delete operations."""
        if operation == "INSERT":
            await self.db[collection_name].insert_one(data)
        elif operation == "UPDATE":
            if query is None:
                raise ValueError("Query is required for UPDATE operation")
            await self.db[collection_name].update_one(query, {"$set": data})
        elif operation == "DELETE":
            if query is None:
                raise ValueError("Query is required for DELETE operation")
            await self.db[collection_name].delete_one(query)
        elif operation == "DELETE_MANY":
            if query is None:
                raise ValueError("Query is required for DELETE_MANY operation")
            await self.db[collection_name].delete_many(query)
        elif operation == "UPDATE_MANY":
            if query is None:
                raise ValueError("Query is required for UPDATE_MANY operation")
            await self.db[collection_name].update_many(query, {"$set": data})
        elif operation == "INCREMENT":
            if query is None:
                raise ValueError("Query is required for INCREMENT operation")
            await self.db[collection_name].update_one(query, {"$inc": data})

    async def get_guild_config(self, guild_id):
        """Fetch server configuration or create a new one if it doesn't exist."""
        config = await self.servers_config.find_one({"guild_id": guild_id})
        if not config:
            default_config = {
                "guild_id": guild_id,
                "roles": DEFAULT_ROLES,
                "prefix": PREFIX,
                "testmode": False
            }
            await self.servers_config.insert_one(default_config)
            return default_config
        return config

    async def update_guild_config(self, guild_id, update_data):
        """Update server configuration."""
        await self.servers_config.update_one(
            {"guild_id": guild_id},
            {"$set": update_data},
            upsert=True
        )

    async def set_guild_roles(self, guild_id, roles):
        """Set roles for a specific server."""
        await self.update_guild_config(guild_id, {"roles": roles})

    async def update_role_emojis(self, guild_id, roles):
        """Update role emojis for a specific server."""
        pass

    async def check_testmode(self, guild_id):
        """Check if a server is in test mode."""
        config = await self.get_guild_config(guild_id)
        return config.get("testmode", False)

intents = Intents.default()
intents.message_content = True
intents.members = True

bot = MyBot(intents=intents, command_prefix=PREFIX)
bot.remove_command("help")
if dbl_token:
    bot.topggpy = topgg.DBLClient(bot, dbl_token, autopost=True)

@bot.event
async def on_autopost_success():
    print(f"Posted server count ({bot.topggpy.guild_count}), shard count ({bot.shard_count})")

@bot.before_slash_command_invoke
async def before_invoke_slash(inter):
    if not inter.response.is_done():
        await inter.response.defer()

for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")

bot.run(TOKEN)