# -*- coding: utf-8 -*-

import discord, asyncio
from discord.ext import commands
import mysql.connector
from mysql.connector import errorcode
from time import time
from datetime import datetime
from json import loads, dump
from os import path
from requests import get

from colorama import init, Fore as colour
init(autoreset=True)

""" Configuration. """

# Hardcoded version numbers.
global __version, __abns_version
__version      = 4.51 # Aika (This bot).
__abns_version = 2.20 # Akatsuki's Beatmap Nomination System (#rank-request(s)).
__config_path  = f'{path.dirname(path.realpath(__file__))}/config.json'

# Check for mismatching hardcoded version - config version.
global mismatch
mismatch = 0
with open(__config_path, 'r+', encoding='ascii') as tmp_file:
    tmp_config = loads(tmp_file.read())

    # TODO: check if server build, would not matter for a test env.

    if tmp_config['version'] != __version: # If mismatch, update the old config but store the mismatched version for announce.
        mismatch = tmp_config['version']
        tmp_config['version'] = __version

    tmp_file.seek(0)

    dump(obj=tmp_config, fp=tmp_file, sort_keys=True, indent=4)
    del tmp_config

    tmp_file.truncate()

# Now read the config file for real.
with open(__config_path, 'r', encoding='ascii') as f:
    config = loads(f.read())

# Version numbers from config.
version      = config['version']
abns_version = config['abns_version']

# Aika's discord token.
discord_token = config['discord_token']

# Akatsuki's server/channel IDs.
# [S] = Server. [T] = Text channel. [V] = Voice channel.
akatsuki_server_id           = config['akatsuki_server_id']           # [S] | ID for osu!Akatsuki.
akatsuki_general_id          = config['akatsuki_general_id']          # [T] | ID for #general.
akatsuki_help_id             = config['akatsuki_help_id']             # [T] | ID for #help.
akatsuki_verify_id           = config['akatsuki_verify_id']           # [T] | ID for #verify.
akatsuki_player_reporting_id = config['akatsuki_player_reporting_id'] # [T] | ID for #player_reporting.
akatsuki_rank_request_id     = config['akatsuki_rank_request_id']     # [T] | ID for #rank-request (User).
akatsuki_reports_id          = config['akatsuki_reports_id']          # [T] | ID for #reports.
akatsuki_rank_requests_id    = config['akatsuki_rank_requests_id']    # [T] | ID for #rank-requests (Staff).
akatsuki_botspam_id          = config['akatsuki_botspam_id']          # [T] | ID for #botspam.
akatsuki_nsfw_id             = config['akatsuki_nsfw_id']             # [T] | ID for #nsfw.
akatsuki_friends_only        = config['akatsuki_friends_only']        # [T] | ID for #friends-only.
akatsuki_drag_me_in_voice    = config['akatsuki_drag_me_in_voice']    # [V] | ID for Drag me in (VC).
akatsuki_friends_only_voice  = config['akatsuki_friends_only_voice']  # [V] | ID for ✨cmyui (VC).

mirror_address = config['mirror_address']        # Akatsuki's beatmap mirror (used in ABNS system).
discord_owner  = config['discord_owner_userid']  # Assign discord owner value.
server_build   = config['server_build']          # If we're running a server build.
command_prefix = config['command_prefix']
embed_colour   = int(config['embed_colour'], 16) # Must be casted to int because JSON does not support hex format.
akatsuki_logo  = config['akatsuki_logo']
crab_emoji     = config['crab_emoji']

# A list of filters.
# These are to be used to wipe messages that are deemed inappropriate,
# or break rules. For the most part, these are of other private servers,
# as required by rule #2 of the Akatsuki Discord & Chat Rules
# (https://akatsuki.pw/doc/rules).
filters           = config['filters']           # Direct word for word strcmp.
substring_filters = config['substring_filters'] # Find string in message.

# Max amt of characters where if combined with unicode,
# the user is probably trying to crash Discord clients.
crashing_intent_length = config['crashing_intent_length']

# A list of message (sub)strings that we will use to deem
# a quantifiable value for the "quality" of a message.
low_quality   = config['low_quality']  # Deemed a "low-quality" message  (usually profanity).
high_quality  = config['high_quality'] # Deemed a "high-quality" message (usually professionality & proper grammar).


""" Attempt to connect to MySQL. """
try: cnx = mysql.connector.connect(
        user       = config['mysql_user'],
        password   = config['mysql_passwd'],
        host       = config['mysql_host'],
        database   = config['mysql_database'],
        autocommit = True,
        use_pure   = True)
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        raise Exception('Something is wrong with your username or password.')
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        raise Exception('Database does not exist.')
    else: raise Exception(err)
else: SQL = cnx.cursor()


""" Functions. """
def safe_discord(s):
    return str(s).replace('`', '')

def get_prefix(client, message):
    return commands.when_mentioned_or(*[config['command_prefix']])(client, message)

def is_admin(author):
    return True if author.guild_permissions.manage_messages else False

#bot.change_presence(activity=discord.Game(name="osu!Akatsuki", url="https://akatsuki.pw/", type=1))
client = discord.Client(
    max_messages      = 2500,
    heartbeat_timeout = 20
)

bot = commands.Bot(
    command_prefix   = get_prefix,
    case_insensitive = True,
    help_command     = None,
    self_bot         = False,
    owner_id         = discord_owner
)

# Load cogs.
[bot.load_extension(i) for i in ['cogs.staff', 'cogs.user']]

@bot.event
async def on_ready():
    print('=' * 40,
          f'Logged in as {bot.user.name}\n',
          f'UserID: {bot.user.id}',
          f'Version: {version}',
          f'ABNS Version: {abns_version}',
          f'Owner: {discord_owner}',
          f'Filters: {len(filters)} | {len(substring_filters)}',
          '=' * 40,
          end='\n\n',
          sep='\n'
    )

    if server_build and mismatch:
        # Configure, and send the embed to #general.
        announce_online = discord.Embed(
            title       = f"Aika has been updated to v{__version:.2f}. (Previous: v{mismatch:.2f})",
            description = "Ready for commands <3\n\n"
                          "Aika is osu!Akatsuki's [open source](https://github.com/osuAkatsuki/Aika) discord bot.\n\n"
                          "[Akatsuki](https://akatsuki.pw)\n"
                          "[Support Akatsuki](https://akatsuki.pw/support)",
            color       = 0x00ff00)                                     \
        .set_footer(icon_url=crab_emoji, text="Thank you for playing!") \
        .set_thumbnail(url=akatsuki_logo)

        await bot.get_channel(akatsuki_general_id).send(embed=announce_online)
    return


@bot.event
async def on_member_update(before, after):
    """
    Called when a Member updates their profile.

    This is called when one or more of the following things change:
      - status
      - activity
      - nickname
      - roles

    Parameters
        before (Member) – The updated member’s old info.
        after (Member) – The updated member’s updated info.
    """
    if before.nick == after.nick or not after.nick:
        return

    non_ascii = 0

    for i in after.nick:
        if ord(i) > 127:
            non_ascii += 1

    if non_ascii < len(after.nick) / 2:
        return

    try:
        await after.edit(nick=before.nick)
        # Perhaps send the user a message if changed?
    except discord.errors.Forbidden:
        print(f"{colour.LIGHTRED_EX}Insufficient permissions to change new nickname '{after.nick}'.")


@bot.event
async def on_message_edit(before, after):
    if after.channel.id != akatsuki_botspam_id:
        col = None
        if not after.guild:                         col = colour.GREEN
        elif 'cmyui' in after.content.lower():      col = colour.YELLOW
        elif after.guild.id == akatsuki_server_id:  col = colour.CYAN

        m_start = f'[EDIT] {datetime.now():%Y-%m-%d %H:%M:%S} [{after.guild} #{after.channel}] {after.author}:\n'

        m_end = []
        for line in after.content.split('\n'): m_end.append(f'{4 * " "}{line}') # I know theres a better way to do this in py, I just can't remember it.
        m_end = '\n'.join(m_end)

        with open(f'{path.dirname(path.realpath(__file__))}/discord.log', 'a+') as log: log.write(f'\n{m_start}{m_end}')

        print(f'{col}{m_start}{colour.RESET}{m_end}')

    # Ignore any member with discord's "manage_messages" permissions.
    # Filter messages with our filters & substring_filters.
    if not is_admin(after.author):
        for split in after.content.lower().split(' '):
            if any(i == split for i in filters) or any(i in after.content.lower() for i in substring_filters):
                await after.delete()

                print(f'{colour.LIGHTYELLOW_EX}^ Autoremoved message ^')
                try:
                    await after.author.send(
                        'Hello,\n\n'
                        'Your message in osu!Akatsuki has been removed as it has been deemed unsuitable.\n\n'
                        f'If you have any questions, please ask <@{discord_owner}>.\n'
                        '**Do not try to evade this filter as it is considered fair ground for a ban**.\n\n'
                        f'```{safe_discord(f"{after.author.name}: {after.content}")}```'
                    )
                except: print(f'{colour.LIGHTRED_EX}Could not warn {after.author.name}.')

                cnx.ping(reconnect=True, attempts=2, delay=1)

                SQL.execute('INSERT INTO profanity_logs (id, user, content, datetime) VALUES (NULL, %s, %s, %s)',
                    [after.author.id, after.content.encode('ascii', errors='ignore'), time()])

                return


@bot.event
async def on_voice_state_update(member, before, after): # TODO: check if they left dragmein, and delete embed.. if that's even possible..

    # Only use this event for the "drag me in" voice channel.
    if not after.channel or after.channel.id != akatsuki_drag_me_in_voice: return

    # Create our vote embed.
    embed = discord.Embed(
        title       = f'{member} wants to be dragged in.',
        description = 'Please add a reaction to determine their fate owo..',
        color       = 0x00ff00)                                             \
    .set_footer(icon_url = crab_emoji, text = 'Only one vote is required.') \
    .set_thumbnail(url   = akatsuki_logo)

    # Assign friends-only chat and voice channel as constants.
    friends_only_text  = bot.get_channel(akatsuki_friends_only)
    friends_only_voice = bot.get_channel(akatsuki_friends_only_voice)

    # Send our embed, and add our base 👍.
    msg = await friends_only_text.send(embed=embed)
    await msg.add_reaction('👍')

    def check(reaction, user): # TODO: safe
        print(reaction, reaction.emoji, user, user.voice, friends_only_voice,sep='\n\n')
        if user in [member, bot.user]: return False
        return reaction.emoji == '👍' and user.voice.channel == friends_only_voice

    # Wait for a 👍 from a "friend". Timeout: 5 minutes.
    try:
        _, user = await bot.wait_for('reaction_add', timeout=5 * 60, check=check)
    except asyncio.TimeoutError: # Timed out. Remove the embed.
        await friends_only_text.send(f"Timed out {member}'s join query.")
        await msg.delete()
        return

    try: await member.move_to(channel=friends_only_voice, reason='Voted in.')
    except discord.errors.HTTPException: await msg.delete(); return

    # Send our vote success, and delete the original embed.
    await friends_only_text.send(f'{user} voted {member} in.')
    await msg.delete()
    return


@bot.event
async def on_message(message):

    # The message has no content.
    # Don't bother doing anything with it.
    if not message.content: return

    # Regular user checks.
    if message.author.id != discord_owner:

        # Verification channel.
        if message.channel.id == akatsuki_verify_id:
            if not message.content.split(' ')[-1].isdigit(): # bot
                await message.author.add_roles(discord.utils.get(message.guild.roles, name='Members'))
                await bot.get_channel(akatsuki_general_id).send(f'Welcome to osu!Akatsuki <@{message.author.id}>!')

            await message.delete() # Delete all messages posted in #verify.
            return

        # If we have unicode in a long message,
        # it's probably either with crashing intent,
        # or is just low quality to begin with?
        if  any(ord(char) > 127 for char in message.content) \
        and len(message.content) >= crashing_intent_length:
            await message.delete()
            return

    else: # Owner checks.
        if  len(message.content) > 5 \
        and message.content[1:7] == 'reload':
            cog_name = message.content[9:].lower()
            if cog_name in ('staff', 'user'):
                bot.reload_extension(f'cogs.{cog_name}')
                await message.channel.send(f'Reloaded extension {cog_name}.')
            else:
                await message.channel.send(f'Invalid extension {cog_name}.')
            return


    # NSFW channel checks (deleting non-images from #nsfw).
    if message.channel.id == akatsuki_nsfw_id:
        def check_content(m): # Don't delete links or images.
            if any(message.content.startswith(s) for s in ('http://', 'https://')) or message.attachments: return False
            return True

        if check_content(message): await message.delete()
        return


    # Message sent in #rank-request, move to #rank-requests.
    if message.channel.id == akatsuki_rank_request_id:
        await message.delete()

        if not any(required in message.content for required in ('akatsuki.pw', 'osu.ppy.sh')) \
        or len(message.content) > 60                                                          \
        or len(message.content) < 20:
            await message.author.send('Your beatmap request was incorrectly formatted, and thus has not been submitted.')
            return

        # Support both links like "https://osu.ppy.sh/b/123" AND "osu.ppy.sh/b/123".
        # Also allow for /s/, /b/, and /beatmapset/setid/discussion/mapid links.
        partitions = message.content.split('/')[3 if '://' in message.content else 1:]

        # Yea thank you for sending something useless in #rank-request very cool.
        if partitions[0] not in ('s', 'b', 'beatmapsets'): return

        beatmapset = partitions[0] in ('s', 'beatmapsets') # Link is a beatmapset_id link, not a beatmap_id link.
        map_id = partitions[1] # Can be SetID or MapID.

        cnx.ping(reconnect=True, attempts=2, delay=1)

        if not beatmapset: # If the user used a /b/ link, let's turn it into a set id.
            SQL.execute('SELECT beatmapset_id FROM beatmaps WHERE beatmap_id = %s LIMIT 1', [map_id])
            map_id = SQL.fetchone()[0]

        # Do this so we can check if any maps in the set are ranked or loved.
        # If they are, the QAT have most likely already determined statuses of the map.
        SQL.execute('SELECT mode, ranked FROM beatmaps WHERE beatmapset_id = %s ORDER BY ranked DESC LIMIT 1', [map_id])
        sel = SQL.fetchone()

        if not sel: # We could not find any matching rows with the map_id.
            await message.author.send('The beatmap could not be found in our database.')
            return

        mode, status = sel

        if status in (2, 5): # Map is already ranked/loved
            await message.author.send(f"Some (or all) of the difficulties in the beatmap you requested already seem to be {'ranked' if status == 2 else 'loved'}"
                                       " on the Akatsuki server!\n\nIf this is false, please contact a BN directly to proceed.")
            return

        # Sort out mode to be used to check difficulty.
        # Also have a formatted one to be used for final post.
        if   mode == 0: mode, mode_formatted = 'std',   'osu!'
        elif mode == 1: mode, mode_formatted = 'taiko', 'osu!taiko'
        elif mode == 2: mode, mode_formatted = 'ctb',   'osu!catch'
        else:           mode, mode_formatted = 'mania', 'osu!mania'

        # Select map information.
        SQL.execute(f'SELECT song_name, ar, od, max_combo, bpm, difficulty_{mode} FROM beatmaps WHERE beatmapset_id = %s ORDER BY difficulty_{mode} DESC LIMIT 1', [map_id])
        song_name, ar, od, max_combo, bpm, star_rating = SQL.fetchone()

        # Temp disabled
        #artist = loads(get(f'{mirror_address}/api/s/{map_id}', timeout=1.5).text)['Creator']
        #.add_field (name = "Mapper",            value = artist)                          \

        # Create embeds.
        embed = discord.Embed(
            title = 'A new beatmap request has been recieved.',
            description = '** **',
            color       = embed_colour
            )                                                                                             \
        .set_image (url  = f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")        \
        .set_author(url  = f"https://akatsuki.pw/d/{map_id}", name = song_name, icon_url = akatsuki_logo) \
        .set_footer(text = f"Akatsuki's beatmap nomination system v{abns_version:.2f}", icon_url = "https://nanahira.life/MpgDe2ssQ5zDsWliUqzmQedZcuR4tr4c.jpg") \
        .add_field (name = "Nominator",         value = message.author.name)             \
        .add_field (name = "Gamemode",          value = mode_formatted)                  \
        .add_field (name = "Highest SR",        value = f"{star_rating:.2f}*")           \
        .add_field (name = "Highest AR",        value = ar)                              \
        .add_field (name = "Highest OD",        value = od)                              \
        .add_field (name = "Highest Max Combo", value = f"{max_combo}x")                 \
        .add_field (name = "BPM",               value = bpm)

        # Prepare, and send the report to the reporter.
        embed_dm = discord.Embed(
            title       = "Your beatmap nomination request has been sent to Akatsuki's Beatmap Nomination Team for review.",
            description = 'We will review it shortly.',
            color       = 0x00ff00
            )                                                                                               \
        .set_thumbnail(url  = akatsuki_logo)                                                                \
        .set_image    (url  = f"https://assets.ppy.sh/beatmaps/{map_id}/covers/cover.jpg?1522396856")       \
        .set_footer   (text = f"Akatsuki's beatmap nomination system v{abns_version:.2f}", icon_url = crab_emoji)

        # Send the embed to the #rank_requests channel.
        request_post = await bot.get_channel(akatsuki_rank_requests_id).send(embed=embed)

        # Send the embed to the nominator by DM. TODO: check if we can message the user rather than abusing try-except? that might just be slower lul
        try: await message.author.send(embed=embed_dm)
        except: print(f'Could not DM ({message.author.name}).')

        for i in ['👎', '👍']: await request_post.add_reaction(i)
        return


    # Message sent in #player-reporting, move to #reports.
    if message.channel.id == akatsuki_player_reporting_id:
        await message.delete() # Delete the message from #player-reporting.

        # Prepare, and send the report in #reports.
        embed = discord.Embed(title = 'New report recieved.', description='** **', color=0x00ff00)     \
        .set_thumbnail       (url   = akatsuki_logo)                                                   \
        .add_field           (name  = 'Report content', value = message.content,        inline = True) \
        .add_field           (name  = 'Author',         value = message.author.mention, inline = True)

        # Prepare, and send the report to the reporter.
        embed_pm = discord.Embed(
            title       = 'Thank you for the player report.',
            description = 'We will review the report shortly.',
            color       = 0x00ff00)                                                     \
        .add_field    (name = 'Report content', value = message.content, inline = True) \
        .set_thumbnail(url  = akatsuki_logo)

        if not message.content.startswith(command_prefix): # Do not pm or link to #reports if it is a command.
            await message.author.send(embed=embed_pm)
            await bot.get_channel(akatsuki_reports_id).send(embed=embed)
        return

    elif message.author != bot.user and message.guild:
        # Message sent in #help, log to db.
        if message.channel.id == akatsuki_help_id:
            # Split the content into sentences by periods.
            # TODO: Other punctuation marks!
            sentence_split = message.content.split('.')

            # Default values for properly formatted messages / negative messages.
            properly_formatted, negative = [False] * 2

            # After every period, check they have a space and the next sentence starts with a capital letter (ignore things like "...").
            for idx, sentence in enumerate(sentence_split):
                if len(sentence) > 1 and idx:
                    if sentence[0] == ' ' and sentence[1].isupper(): continue
                    negative = True

            properly_formatted = \
                message.content[0].isupper() \
                and message.content[len(message.content) - 1] in ('.', '?', '!') \
                and not negative

            quality = 1

            if any(i in message.content.lower() for i in low_quality):                          quality -= 1
            elif any(i in message.content.lower() for i in high_quality) or properly_formatted: quality += 1

            cnx.ping(reconnect=True, attempts=2, delay=1)

            # TODO: Store the whole bitch in a single number.
            # Maybe even do some bitwise black magic shit.
            SQL.execute('INSERT INTO help_logs (id, user, content, datetime, quality) VALUES (NULL, %s, %s, %s, %s)',
                [message.author.id, message.content.encode('ascii', errors='ignore'), time(), quality])

        if message.channel.id != akatsuki_botspam_id:
            col = None
            if not message.guild:                         col = colour.GREEN
            elif 'cmyui' in message.content.lower():      col = colour.YELLOW
            elif message.guild.id == akatsuki_server_id:  col = colour.CYAN

            m_start = f'{datetime.now():%Y-%m-%d %H:%M:%S} [{message.guild} #{message.channel}] {message.author}:\n'

            m_end = []
            for line in message.content.split('\n'): m_end.append(f'{4 * " "}{line}') # I know theres a better way to do this in py, I just can't remember it.
            m_end = '\n'.join(m_end)

            with open(f'{path.dirname(path.realpath(__file__))}/discord.log', 'a+') as log: log.write(f'\n{m_start}{m_end}')

            print(f'{col}{m_start}{colour.RESET}{m_end}')

        # Ignore any member with discord's "manage_messages" permissions.
        # Filter messages with our filters & substring_filters.
        if not is_admin(message.author):
            for split in message.content.lower().split(' '):
                if any(i == split for i in filters) or any(i in message.content.lower() for i in substring_filters):
                    await message.delete()

                    print(f'{colour.LIGHTYELLOW_EX}^ Autoremoved message ^')
                    try:
                        await message.author.send(
                            'Hello,\n\n'
                            'Your message in osu!Akatsuki has been removed as it has been deemed unsuitable.\n\n'
                           f'If you have any questions, please ask <@{discord_owner}>.\n'
                            '**Do not try to evade this filter as it is considered fair ground for a ban**.\n\n'
                           f'```{safe_discord(f"{message.author.name}: {message.content}")}```'
                        )
                    except: print(f'{colour.LIGHTRED_EX}Could not warn {message.author.name}.')

                    cnx.ping(reconnect=True, attempts=2, delay=1)

                    SQL.execute('INSERT INTO profanity_logs (id, user, content, datetime) VALUES (NULL, %s, %s, %s)',
                        [message.author.id, message.content.encode('ascii', errors='ignore'), time()])

                    return

        # Finally, process commands.
        await bot.process_commands(message)
    return

bot.run(discord_token, bot=True, reconnect=True)

# Clean up
print('\nKeyboardInterrupt detected. Powering down Aika..')
SQL.close()
cnx.close()
print('Cleaning complete.')
