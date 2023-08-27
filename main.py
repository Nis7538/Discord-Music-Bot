import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

# Remove the default help command
bot.remove_command('help')

# Print statement when the bot is ready
@bot.event
async def on_ready():
    print("Bot is running")

# Load all cogs
async def load():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

# Start the bot with our token
async def main():
    async with bot:
        await load()
        await bot.start(os.getenv("TOKEN"))

asyncio.run(main())