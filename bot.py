import discord
from discord.ext import commands
import os
import asyncio
import wikipediaapi
import logging
from dotenv import load_dotenv  # Import load_dotenv from dotenv

# Load environment variables from .env file
load_dotenv()  # Load .env variables at the beginning of your script

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
    language='en',  # Specify the Wikipedia language (e.g., 'en' for English)
    user_agent="SmartGuy/1.0",  # Set your bot's name and version as the user agent
)

# Dictionary to store the listening channels for each guild
listening_channels = {}

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
    # Check if the user has the 'manage_channels' permission (guild owner typically has it)
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
            listening_channels = eval(data)  # Load as a dictionary
    except FileNotFoundError:
        listening_channels = {}  # Initialize as an empty dictionary

# Function to save listening channels to a file
def save_listening_channels():
    with open('listening_channels.txt', 'w') as file:
        file.write(str(listening_channels))  # Save as a string representation of the dictionary

# Function to send messages with pagination buttons and edit the existing message
async def send_paginated_messages(channel, messages):
    current_page = 0
    total_pages = len(messages)
    message = None

    while True:
        # Create an embed with the current page content
        embed = discord.Embed(
            title=f'Page {current_page + 1}/{total_pages}',
            description=messages[current_page],
            color=discord.Color.blue()
        )

        # Edit the existing message or send a new one if it doesn't exist
        if message:
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)

        # Add reaction buttons
        if total_pages > 1:
            await message.add_reaction('◀️')  # Backward
            await message.add_reaction('▶️')  # Forward

        try:
            reaction, user = await bot.wait_for(
                'reaction_add',
                timeout=60.0,
                check=lambda r, u: r.message.id == message.id and u != bot.user
            )

            if str(reaction) == '▶️' and current_page < total_pages - 1:
                current_page += 1
            elif str(reaction) == '◀️' and current_page > 0:
                current_page -= 1

            # Remove the user's reaction
            await message.remove_reaction(reaction, user)

        except asyncio.TimeoutError:
            # Stop pagination after a minute of inactivity
            break

        await asyncio.sleep(1)  # Add a slight delay to prevent API abuse

# Function to research the user's message (fetch information from Wikipedia and send a reply with pagination)
async def research_message(query, channel):
    try:
        # Use the Wikipedia API to fetch information
        page = wiki_wiki.page(query)

        if page.exists():
            # Split the Wikipedia page content into chunks based on sentences
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

            # Send messages with pagination
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
        return  # Ignore messages sent by the bot itself

    if message.guild:
        # Check if the message is in the listening channel for the guild
        guild_id = message.guild.id
        if guild_id in listening_channels:
            listening_channel_id = listening_channels[guild_id]
            if message.channel.id == listening_channel_id:
                # Your message processing logic here
                await research_message(message.content, message.channel)

    # Allow other event handlers to process the message
    await bot.process_commands(message)


# Run the bot with your token
bot.run(TOKEN)  # Use the TOKEN variable
