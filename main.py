import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Import all COG's
from help import help
from music import music

load_dotenv()

bot = commands.Bot(command_prefix='!')

# Remove the default help command
bot.remove_command('help')

# Register class with the bot
bot.add_cog(help(bot))
bot.add_cog(music(bot))

# Start the bot with our token
bot.run(os.getenv("TOKEN"))
