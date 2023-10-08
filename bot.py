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
    user_agent="SmartGuy/1.0",  # Set your bot's name and version as the user agent
)

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
async def setchannel(ctx, channel: discord.TextChannel):
    # Check if the user has the 'manage_channels' permission (guild owner typically has it)
    if ctx.author.guild_permissions.manage_channels:
        # Store the channel ID in an environment variable
        os.environ['BOT_CHANNEL_ID'] = str(channel.id)
        await ctx.send(f'Listening for messages in {channel.mention}')
    else:
        await ctx.send('You need to have the "Manage Channels" permission to set the channel.')

# Function to research the user's message (fetch information from Wikipedia and send a reply in the same channel)
async def research_message(query, channel, user):
    try:
        # Use the Wikipedia API to fetch information
        page = wiki_wiki.page(query)
        
        if page.exists():
            # Split the Wikipedia page content into chunks of 2000 characters for embeds
            page_content = page.text
            chunks = [page_content[i:i + 2000] for i in range(0, len(page_content), 2000)]
            
            for index, chunk in enumerate(chunks):
                # Create an embed
                embed = discord.Embed(
                    title=f'Q. {query} (Part {index+1})',
                    description=chunk,
                    color=discord.Color.blue()
                )
                embed.set_author(name=user.display_name)  # Set author name and pfp
                embed.set_footer(text=f'Part {index+1}/{len(chunks)} | Source: Wikipedia')  # Include source in the footer
                
                # Send the embed as a message in the same channel
                await channel.send(embed=embed)
                
            # Send a button to the full Wikipedia page
            await channel.send(
                "View Full Page on Wikipedia",
                components=[
                    discord.ui.Button(
                        label="Wikipedia",
                        url=page.fullurl,
                        style=discord.ButtonStyle.link
                    )
                ]
            )
        else:
            await channel.send("No information found on Wikipedia.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        await channel.send("An error occurred while fetching information.")

# Event handler for when a message is sent in the specified channel
@bot.event
async def on_message(message):
    # Check if the message is in the specified channel
    bot_channel_id = os.environ.get('BOT_CHANNEL_ID')
    
    if message.channel.id == int(bot_channel_id):
        # Check if the message author is not the bot itself
        if message.author != bot.user:
            # Your message processing logic here
            await research_message(message.content, message.channel, message.author)
    
    # Allow other event handlers to process the message
    await bot.process_commands(message)

# Run the bot with your token from the .env file
bot.run(os.environ['DISCORD_TOKEN'])
