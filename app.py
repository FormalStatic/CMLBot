import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, has_permissions
import json
from dotenv import dotenv_values

# Load environment variables from .env file
config = dotenv_values(".env")

# Create a Discord bot instance
bot = discord.Bot()

# Load or initialize user_elo data
with open('user_elo.json', encoding='utf-8') as w:
    try:
        user_elo = json.load(w)
    except ValueError:
        user_elo = {}
        user_elo['users'] = []

# Command to ping the bot
@bot.command(description="ping the bot")
async def ping(ctx):
    await ctx.respond("pong!")

# Command to set elo for a user (requires manage_roles and ban_members permissions)
@bot.command(pass_context=True)
@has_permissions(manage_roles=True, ban_members=True)
async def elo_set(ctx, user: discord.User, elo: int):
    author = ctx.author

    if not elo:
        await ctx.send("Please provide an amount of elo")
        return

    # Create an embed to display the elo setting
    embed = discord.Embed(
        title=f"{user.name}'s elo has been set!",
        description=f"**{author.mention} has set {user.mention}'s elo to {elo}!**",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=user.avatar.url)
    await ctx.respond(embed=embed)

    # Update user_elo data
    user_found = False
    for current_user in user_elo['users']:
        if current_user['name'] == user.name:
            current_user['elo'] = elo  # Set the 'elo' key to a single value
            user_found = True
            break

    if not user_found:
        user_elo['users'].append({
            'name': user.name,
            'elo': elo
        })

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)

# Command to check elo for a user
@bot.command(pass_context=True)
async def elo(ctx, user: discord.User):
    for current_user in user_elo['users']:
        if user.name == current_user['name']:
            message = current_user['elo']
            embed = discord.Embed(title=f"{user.display_name}'s elo", description=f"## {message}", color=discord.Color.green())
            embed.set_thumbnail(url=user.avatar.url)
            await ctx.respond(embed=embed)
            break
    else:
        embed = discord.Embed(title=f"{user.display_name}'s elo", description=f"{user.mention} is unrated!", color=discord.Color.light_grey())
        embed.set_thumbnail(url=user.avatar.url)
        await ctx.respond(embed=embed)

# Run the bot with the provided token from the .env file
bot.run(config["TOKEN"])
