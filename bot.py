import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import wikipediaapi

# Define the intents you need (for message events)
intents = discord.Intents.default()
intents.message_content = True

# Load environment variables from .env file
load_dotenv()

# Initialize the bot with intents
bot = commands.Bot(command_prefix='/', intents=intents)

# Create a Wikipedia API client with a user agent
wiki_wiki = wikipediaapi.Wikipedia(
    language='en',  # Specify the Wikipedia language (e.g., 'en' for English)
    user_agent="YourBotName/1.0",  # Set your bot's name and version as the user agent
)

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
async def set_channel(ctx, channel: discord.TextChannel):
    # Check if the user has the 'manage_channels' permission (guild owner typically has it)
    if ctx.author.guild_permissions.manage_channels:
        # Store the channel ID in an environment variable
        os.environ['BOT_CHANNEL_ID'] = str(channel.id)
        await ctx.send(f'Listening for messages in {channel.mention}')
    else:
        await ctx.send('You need to have the "Manage Channels" permission to set the channel.')

# Event handler for when a message is sent in the specified channel
@bot.event
async def on_message(message):
    # Check if the message is in the specified channel
    bot_channel_id = os.environ.get('BOT_CHANNEL_ID')
    
    if message.channel.id == int(bot_channel_id):
        # Check if the message author is not the bot itself
        if message.author != bot.user:
            # Your message processing logic here
            response = research_message(message.content)
            await message.channel.send(response)
    
    # Allow other event handlers to process the message
    await bot.process_commands(message)

# Function to research the user's message (fetch information from Wikipedia)
def research_message(query):
    try:
        # Use the Wikipedia API to fetch information
        page = wiki_wiki.page(query)
        
        if page.exists():
            # Return the summary of the Wikipedia page
            return page.summary[:2000]  # Truncate to 2000 characters to avoid Discord message limit
        else:
            return "No information found on Wikipedia."
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "An error occurred while fetching information."

# Run the bot with your token from the .env file
bot.run(os.environ['DISCORD_TOKEN'])
