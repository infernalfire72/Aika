import discord
from discord.ext import commands
from datetime import datetime as d
import mysql.connector
from mysql.connector import errorcode
import configparser
import time
import hashlib
import re

# Error response strings.
INSUFFICIENT_PRIVILEGES  = "You do not have sufficient privileges for this command."
INCORRECT_SYNTAX         = "You have used the incorrect syntax for this command."
INCORRECT_NUMBER_OF_ARGS = "You have specified an invalid number of arguments for this command."

# For FAQ
AKATSUKI_IP_ADDRESS      = "51.79.17.191"     # Akatsuki's osu! server IP.

# Akatsuki's logo.
# To be used mostly for embed thumbnails.
AKATSUKI_LOGO            = "https://akatsuki.pw/static/logos/logo.png"


# Configuration.
config = configparser.ConfigParser()
config.sections()
config.read("config.ini")

# MySQL
try:
    cnx = mysql.connector.connect(
        user       = config['mysql']['user'],
        password   = config['mysql']['passwd'],
        host       = config['mysql']['host'],
        database   = config['mysql']['db'],
        autocommit = True)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your username or password.")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist.")
    else:
        print(err)
else:
    SQL = cnx.cursor()

class User(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name        = "faq",
        description = "Frequently asked questions.",
        aliases     = ['info', 'information'],
        usage       = "<callback>"
    )
    async def faq_command(self, ctx):
        text = ctx.message.content[len(ctx.prefix) + len(ctx.invoked_with) + 1:]

        # 0 = info : 1 = faq
        command_type = 0 if ctx.invoked_with.startswith("info") else 1

        callback = text.split(" ")[0]

        SQL.execute("SELECT * FROM discord_faq WHERE topic = %s AND type = %s", [callback, command_type])
        result = SQL.fetchone()

        if callback == "" or result is None:
            SQL.execute("SELECT id, topic, title FROM discord_faq WHERE type = %s", [command_type])

            faq_db = SQL.fetchall()

            faq_list = ""
            for idx, val in enumerate(faq_db):
                faq_list += f"{idx + 1}. {val[1]}{' ' * (12 - len(val[1]))}|| {val[2]}\n"

            await ctx.send(f"{'I could not find a topic by that name.' if len(callback) else ''}\n```{faq_list.replace('`', '')}```")
        else:
            embed = discord.Embed(title=result[2], description='** **', color=0x00ff00)
            embed.set_thumbnail(url=AKATSUKI_LOGO)
            embed.add_field(
                name   = "** **",
                value  = result[3]
                            .replace("{AKATSUKI_IP}", AKATSUKI_IP_ADDRESS)
                            .replace("{COMMAND_PREFIX}", ctx.prefix),
                inline = result[5])

            if result[4] is not None:
                embed.set_footer(icon_url='', text=result[4])
            await ctx.send(embed=embed)
        return

    @commands.command(
        name        = "rewrite",
        description = "Aika's rewrite information.",
        aliases     = ['recent', 'stats', 'linkosu', 'botinfo', 'aika', 'cmyui', 'apply', 'akatsuki']
    )
    async def rewrite_info(self, ctx):
        await ctx.send(f"**Aika is currently undergoing a rewrite, and the {ctx.invoked_with} command has not yet been implemented.**\n"
                        "\n"
                        "Repository: https://github.com/osuAkatsuki/Aika.\n"
                        "Sorry for the inconvenience!")
        return

    @commands.command(
        name        = "nsfw",
        description = "Grants access to the NSFW channels of Akatsuki.",
        aliases     = ['nsfwaccess']
    )
    async def nsfw_access(self, ctx): # TODO: toggle or check if already has access
        def check(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author

        await ctx.send("Please type `Yes` to confirm you are over the age of 18.\n"
                       "If you falsely accept this, you will be permanently banned from the discord.")

        msg = await self.bot.wait_for("message", check=check)
        resp = msg.content.lower() == "yes"
        if resp:
            await ctx.author.add_roles(discord.utils.get(ctx.message.guild.roles, name="NSFW Access"))
            await ctx.send("You should now have access to the NSFW channels.")
        return

    @commands.command(
        name        = "time",
        description = "Returns the current UNIX time.",
        aliases     = ['unix', 'unixtime']
    )
    async def current_unixtime(self, ctx):
        await ctx.send(f"Current UNIX timestamp: `{int(time.time())}`") # int cast to round lol
        return

    @commands.command(
        name        = "hash",
        description = "Returns the current MD5 of the input string.",
        aliases     = ['encrypt']
    )
    async def hash_string(self, ctx):
        hash_type = ctx.message.content.split(' ')[1].lower()
        if hash_type not in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512"):
            await ctx.send(f"{hash_type} is not a supported algorithm.")
            return

        string = ''.join(ctx.message.content.split(' ')[2:]).encode('utf-8')

        if hash_type == "md5":
            r = hashlib.md5(string).hexdigest()
        elif hash_type == "sha1":
            r = hashlib.sha1(string).hexdigest()
        elif hash_type == "sha224":
            r = hashlib.sha224(string).hexdigest()
        elif hash_type == "sha256":
            r = hashlib.sha256(string).hexdigest()
        elif hash_type == "sha384":
            r = hashlib.sha384(string).hexdigest()
        elif hash_type == "sha512":
            r = hashlib.sha512(string).hexdigest()

        await ctx.send(f"{hash_type.upper()}: `{r}`")
        return

    @commands.command(
        name        = "round",
        description = "Returns arg0 rounded to arg1 decimal places."
    )
    async def round_number(self, ctx):
        fuckpy = None
        if re.match("^\d+?\.\d+?$", ctx.message.content.split(' ')[1]) is None:
            await ctx.send("Why are your trying to round that?")
            return

        if len(ctx.message.content.split(' ')[1].split(".")[1]) < int(ctx.message.content.split(' ')[2]):
            fuckpy = len(ctx.message.content.split(' ')[1].split(".")[1])

        await ctx.send(f"Rounded value (decimal places: {ctx.message.content.split(' ')[2] if not fuckpy else fuckpy}): `{round(float(ctx.message.content.split(' ')[1]), int(ctx.message.content.split(' ')[2]))}`")
        return

def setup(bot):
    bot.add_cog(User(bot))