import discord
from discord.ext import commands
import os
import asyncio
import wikipediaapi
import logging
from dotenv import load_dotenv
import cachetools

# Load environment variables from .env file
load_dotenv()

# Get the bot token from the environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the intents you need (for message events)
intents = discord.Intents.default()
intents.message_content = True

# Initialize the bot with intents
bot = commands.Bot(command_prefix='/', intents=intents)

# Create a Wikipedia API client with a user agent
wiki_wiki = wikipediaapi.Wikipedia(
    language='en',
    user_agent="SmartGuy/1.0",
)

# Dictionary to store the listening channels for each guild
listening_channels = {}

# Create a cache for Wikipedia API responses
cache = cachetools.LRUCache(maxsize=100)  # You can adjust the cache size as needed

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    
    # Load saved listening channels from a file (if available)
    load_listening_channels()

# Command to set the listening channel
@bot.command(
    name="setchannel",
    description="Set the channel where the bot should listen.",
)
async def set_channel(ctx, channel: discord.TextChannel):
    # Check if the user has the 'manage_channels' permission
    if ctx.author.guild_permissions.manage_channels:
        # Store the channel ID in the dictionary
        listening_channels[ctx.guild.id] = channel.id
        
        # Save the listening channels to a file
        save_listening_channels()
        
        await ctx.send(f'Listening for messages in {channel.mention}')
    else:
        await ctx.send('You need to have the "Manage Channels" permission to set the channel.')

# Function to load saved listening channels from a file
def load_listening_channels():
    global listening_channels
    try:
        with open('listening_channels.txt', 'r') as file:
            data = file.read()
            listening_channels = eval(data)
    except FileNotFoundError:
        listening_channels = {}

# Function to save listening channels to a file
def save_listening_channels():
    with open('listening_channels.txt', 'w') as file:
        file.write(str(listening_channels))

# Function to send messages with pagination buttons and edit the existing message
async def send_paginated_messages(channel, messages):
    current_page = 0
    total_pages = len(messages)
    message = None

    while True:
        embed = discord.Embed(
            title=f'Page {current_page + 1}/{total_pages}',
            description=messages[current_page],
            color=discord.Color.blue()
        )

        if message:
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)

        if total_pages > 1:
            await message.add_reaction('◀️')  # Backward
            await message.add_reaction('▶️')  # Forward
            await message.add_reaction('🔢')  # Go to page

        try:
            def check(reaction, user):
                return reaction.message.id == message.id and user != bot.user

            reaction, user = await bot.wait_for(
                'reaction_add',
                timeout=60.0,
                check=check
            )

            if str(reaction) == '▶️' and current_page < total_pages - 1:
                current_page += 1
            elif str(reaction) == '◀️' and current_page > 0:
                current_page -= 1
            elif str(reaction) == '🔢':
                await message.remove_reaction('🔢', user)
                await user.send(f"Please enter a page number (1-{total_pages}):")

                def page_number_check(m):
                    return m.author == user and m.content.isdigit() and 1 <= int(m.content) <= total_pages

                try:
                    response = await bot.wait_for('message', check=page_number_check, timeout=30.0)
                    current_page = int(response.content) - 1
                except asyncio.TimeoutError:
                    await user.send("You took too long to respond. Page selection canceled.")

            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            break

        await asyncio.sleep(1)  # Add a slight delay to prevent API abuse

# Function to research the user's message (fetch information from Wikipedia and send a reply with pagination)
async def research_message(query, channel):
    try:
        # Check if the response is cached
        if query in cache:
            page = cache[query]
        else:
            # Use the Wikipedia API to fetch information
            page = wiki_wiki.page(query)

            # Cache the response for 5 minutes
            cache[query] = page

        if page.exists():
            sentences = page.text.split(". ")
            chunks = []
            current_chunk = ""

            for sentence in sentences:
                if len(current_chunk + sentence) <= 2000:
                    current_chunk += sentence + ". "
                else:
                    chunks.append(current_chunk)
                    current_chunk = sentence + ". "

            if current_chunk:
                chunks.append(current_chunk)

            await send_paginated_messages(channel, chunks)
        else:
            await channel.send("No information found on Wikipedia.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await channel.send("An error occurred while fetching information.")

# Event handler for when a message is sent
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild:
        guild_id = message.guild.id
        if guild_id in listening_channels:
            listening_channel_id = listening_channels[guild_id]
            if message.channel.id == listening_channel_id:
                await research_message(message.content, message.channel)

    await bot.process_commands(message)

# Command error handling
@set_channel.error
async def set_channel_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Invalid channel. Please mention a valid text channel.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

# Custom help command
bot.remove_command('help')

@bot.command(
    name="help",
    description="Show help and usage information for commands.",
)
async def custom_help(ctx):
    help_message = "Available commands:\n" \
                   "/setchannel <channel_mention>: Set the bot's listening channel.\n" \
                   "/help: Show this help message."

    await ctx.send(help_message)

# Run the bot with your token
bot.run(TOKEN)
