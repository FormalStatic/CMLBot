import discord
from discord.ext import commands
import random
import json
import os
from discord import Option
from datetime import timedelta
from discord.ext.commands import MissingPermissions, has_permissions
from better_profanity import profanity
from dotenv import dotenv_values

config = dotenv_values(".env")  # config = {"USER": "foo", "EMAIL": "foo@example.org"}
bot = discord.Bot()

@bot.command(description="ping the bot")
async def ping(ctx):
  await ctx.respond("pong!")


bot.run(config["TOKEN"])


