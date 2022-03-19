# import all necessary libraries
import os
import discord
from discord import channel
import sqlite3


# set discord intents
intents = discord.Intents(messages=True, guilds=True)
intents.typing = False
intents.presences = False
intents.members = True
intents.reactions = True


# guild_ids for instant sync_commands
guild_ids = [950385625893330966]

# Initialize classes
bot = discord.Bot(command_prefix='$', intents=intents)

# Connect SQL connection
db = sqlite3.connect('data.db')
c = db.cursor()

# Create SQL database if it doesn't exist
c.execute("""CREATE TABLE IF NOT EXISTS features(
    message_id INTEGER,
    feature TEXT,
    kamilVotes INTEGER,
    SDSvotes INTEGER,
    upVotes INTEGER,
    downVotes INTEGER
)""")


# define the 2 trusted members that may add features if the community votes
global SDS, Kamil


@bot.event
async def on_ready():
    """ 
    on_ready is a built-in decorator of discord.Bot that executes when the bot connects to the Discord API.
    """
    print(f'Bot is ready as {bot.user.name}')  # print that the bot is ready
    # set the status of the bot
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

    # get instances of the trusted members
    SDS = await bot.fetch_user(798254943923863612)
    Kamil = await bot.fetch_user(757284325816533174)


@bot.slash_command(description="Send a test message to the bot to see if it is active.", guild_ids=guild_ids)
async def ping(ctx):
    """ 
        Replies to the user with "Pong" and the bot's latency
    """
    embed = discord.Embed(title="Pong! :ping_pong:", colour=0xf73b3b)
    embed.add_field(name="Bot Latency", value=str(
        int(round(bot.latency, 1) * 1000)) + "ms")

    await ctx.send(embed=embed)


class OperatorSelectionView(discord.ui.View):
    """ 
    View sub-class representing a dropdown selection where a member can select a person to implement a feature
    """
    @discord.ui.select(placeholder="Choose an operator to implement this feature.", options=[
        discord.SelectOption(
            label="Kamil", description="Kamil is good at using bots and overall high level options. Choose him for visible server problems"),
        discord.SelectOption(
            label="Soumya", description="Soumya is good at programming and has created this bot. Choose him for problems with the bot.")
    ])
    async def callback(self, select, interaction: discord.Interaction):
        await self.fill_blank_columns(interaction)
        await self.update_db(interaction, select)

    async def fill_blank_columns(self, interaction: discord.Interaction):
        """ 
        Creates column if member does not already have one selected

        Arguments:
            interaction - a discord.Interaction
        """
        cnames = []  # Create a variable with all of the Column Names
        c.execute("""PRAGMA table_info(features);""")
        for i in c.fetchall():
            cnames.append(i[1])

        # Remove all unneccerary columns so that we only have the member columns
        cnames.remove('message_id')
        cnames.remove('feature')
        cnames.remove('kamilVotes')
        cnames.remove('SDSvotes')
        cnames.remove('upVotes')
        cnames.remove('downVotes')

        if not(interaction.user.name in cnames):
            c.execute(
                f"ALTER TABLE features ADD {interaction.user.name} TEXT")
            db.commit()

    async def update_db(self, interaction: discord.Interaction, select):
        """
        Updates the SQLite database with the vote for the operator
        """

        c.execute(
            f"SELECT {interaction.user.name} FROM features WHERE message_id = {interaction.message.id}")

        # if this is the first time the user has voted on this message
        if(c.fetchall()[0][0] == None):
            # get the correct column to increment the vote
            column = 'kamilVotes' if select.values[0] == 'Kamil' else 'SDSvotes' if select. values[0] == 'Soumya' else ''
            # increment the vote
            c.execute(
                f"UPDATE features SET {column} = {column} + 1 WHERE message_id = {interaction.message.id}")
            db.commit()
            # note the current selection
            c.execute(
                f"UPDATE features SET {interaction.user.name} = '{column}' WHERE message_id = {interaction.message.id}"
            )
            db.commit()

            await interaction.response.send_message(
                f"You have selected {select.values[0]}!", ephemeral=True)

        # if this is not the first time the user has voted on this message
        else:
            # get the correct column to increment the vote
            column = 'kamilVotes' if select.values[0] == 'Kamil' else 'SDSvotes' if select. values[0] == 'Soumya' else ''

            # get the previous vote
            c.execute(
                f"SELECT {interaction.user.name} FROM features WHERE message_id = {interaction.message.id}")

            prev_selection = c.fetchall()[0][0]  # save that

            # decrease the previous selection by 1 because that has been un-selected
            c.execute(
                f"UPDATE features SET {prev_selection} = {prev_selection} - 1 WHERE message_id = {interaction.message.id}")
            db.commit()

            # increment the vote
            c.execute(
                f"UPDATE features SET {column} = {column} + 1 WHERE message_id = {interaction.message.id}")
            db.commit()
            # note the current selection
            c.execute(
                f"UPDATE features SET {interaction.user.name} = '{column}' WHERE message_id = {interaction.message.id}"
            )
            db.commit()

            await interaction.response.send_message(
                f"You have changed your selection to {select.values[0]}!", ephemeral=True)


@bot.slash_command(description="Suggest a feature that would greatly benifit the server", guild_ids=guild_ids)
async def request_feature(ctx, feature: str):
    ''' 
    Lets members of the guild to suggest features

    -Part of Community Moderation

    Arguments: 
                feature - A string that is the requested feature

    Output:
                Prints a message in a specified channel(determined by FeatureChannel) and users may react with ⬆️ or ⬇️ to support is dissupport the feature
                Sends a feedback message to the sender of the command, alerting them that the feature has been sent 
    '''

    # sends a temporary message to notify the user that the request is being processed
    reply = await ctx.send("Your feature is being processed...")
    FeatureChannel = bot.get_channel(
        952296010141532210)

    dropdown = OperatorSelectionView()
    # set up the embed to be sent to the channel
    embed = discord.Embed(
        title=f"Feature Request By {ctx.author.name}", colour=0x2adb59)
    embed.add_field(name="Feature Requested", value=feature)
    embed.set_footer(icon_url=ctx.author.avatar.url,
                     text=f"Feature request by {ctx.author.name}")

    message = await FeatureChannel.send(embed=embed, view=dropdown, content="@everyone please check this out and vote for it!")

    # edit the original reply
    await reply.edit(content="Your feature has been processed, check it out in <#952296010141532210>!")

    # add reactions to the feature request
    await message.add_reaction("⬆️")
    await message.add_reaction("⬇️")

    # Create a new row containing the message ID and the feature request to the Database
    c.execute(
        f'INSERT INTO features (message_id, feature, kamilVotes, SDSvotes, upVotes, downVotes) VALUES({message.id}, "{feature}", 0, 0, 0, -1)')
    db.commit()


@bot.event
async def on_raw_reaction_add(payload):
    """
    discord.Bot decorator for when a raw reaction is added

    output:
        Check if the reaction has been added to a feature request, and if so, add that to the SQlite Database
    """
    if payload.guild_id is None:
        return  # Reaction is on a private message

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # Check if the message ID is already in the database
    c.execute(
        f"SELECT message_id FROM features WHERE message_id == {message.id}")
    # If the message is already in the database, then we can continue processing as it means that that is a reaction
    if(len(c.fetchall()) != 0):
        # if the user has upvoted the message
        if str(payload.emoji) == '⬆️':
            # update the database
            c.execute(
                f"UPDATE features SET upVotes = upVotes + 1 WHERE message_id = {message.id}")
            db.commit()

        elif str(payload.emoji) == '⬇️':
            # update the database
            c.execute(
                f"UPDATE features SET downVotes = downVotes + 1 WHERE message_id = {message.id}")
            db.commit()


@bot.event
async def on_raw_reaction_remove(payload):
    """
    discord.Bot decorator for when a raw reaction is removes

    output:
        Check if the reaction has been removed to a feature request, and if so, remove that to the SQlite Database
    """
    if payload.guild_id is None:
        return  # Reaction is on a private message

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    # Check if the message ID is already in the database
    c.execute(
        f"SELECT message_id FROM features WHERE message_id == {message.id}")
    # If the message is already in the database, then we can continue processing as it means that that is a reaction
    if(len(c.fetchall()) != 0):

        # if the user has revoked upvoted the message
        if str(payload.emoji) == '⬆️':
            # update the database
            c.execute(
                f"UPDATE features SET upVotes = upVotes - 1 WHERE message_id = {message.id}")
            db.commit()

        elif str(payload.emoji) == '⬇️':
            # update the database
            c.execute(
                f"UPDATE features SET downVotes = downVotes - 1 WHERE message_id = {message.id}")
            db.commit()


# run the bot
TOKEN = os.environ.get("DISCORD_BOT_SECRET")
bot.run(TOKEN)

# close the connection to the database when the bot goes offline (for modification or such)
print('Closing DB')
db.close()
