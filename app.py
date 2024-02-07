import json
from dotenv import dotenv_values
import datetime
import pytz 

import clipboard
from discord.commands import Option
import discord
from discord.ext import commands, tasks
from discord.ext.commands import MissingPermissions, has_permissions
import discord.utils


months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

# Load environment variables from .env file
config = dotenv_values(".env")

# Create a Discord bot instance
bot = discord.Bot()

webhook = discord.SyncWebhook.from_url(config["WEBHOOK"])

@bot.event
async def on_ready():
    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Up!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Combat Master"))

def calculate_elo(elo, placement, min_elo, max_elo):
    with open('user_elo.json', 'r') as f:
        user_elo = json.load(f)

    k_factor = user_elo["k_factor"]
    # Calculate average elo for comparison
    avg_elo = (min_elo + max_elo) / 2

    # Calculate the expected probability of winning
    expected_prob = 1 / (1 + 10**((avg_elo - elo) / 400))

    # Calculate the new Elo rating with the adjusted term
    if placement < 5:
        new_elo = elo + k_factor * (placement - expected_prob)
    else:
        new_elo = elo - k_factor * (placement - expected_prob)

    # Round to the nearest whole number
    new_elo = round(new_elo)

    return new_elo


def standard_to_military(hour, minute, period):
    """
    Convert standard time to military time.
    
    Args:
    hour (int): Hour in standard format (12-hour clock).
    minute (int): Minute.
    second (int): Second.
    period (str): Time of day period (AM or PM).
    
    Returns:
    tuple: Tuple containing hour, minute, and second in military format.
    """
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0

    return hour, minute

def military_to_standard(time_str):
    """
    Convert military time to standard time.
    
    Args:
    time_str (str): Time string in military format (e.g., "2024-06-26 13:30").
    
    Returns:
    str: Time string in standard format with year, month, day (e.g., "2024-06-26 1:30 PM").
    """
    time_obj = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    year = time_obj.year
    month = time_obj.month
    day = time_obj.day
    hour = time_obj.hour
    minute = time_obj.minute
    
    if hour < 12:
        period = "AM"
        if hour == 0:
            hour = 12
    else:
        period = "PM"
        if hour != 12:
            hour -= 12

    return "{:d}-{:02d}-{:02d} {:d}:{:02d} {}".format(year, month, day, hour, minute, period)


@has_permissions(administrator=True)
@bot.command(description="changes the elo gain/loss intensity")
async def set_k_factor(ctx, k_factor: int):
    # Load user_elo data from the file
    with open('user_elo.json', 'r') as f:
        user_elo = json.load(f)

    # Update the k_factor for the user
    user_elo['k_factor'] = k_factor

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)

    embed = discord.Embed(title=f"K_factor changed!", description=f"K_factor set to {k_factor}!", color=discord.Color.green())
    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ctx.author} changed to the K-factor to {k_factor}")
    await ctx.respond(embed=embed)


@set_k_factor.error
async def timeouterror(ctx, error):
    if isinstance(error, MissingPermissions):
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**You need admin permissions to run this command**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        raise error


# Load user_elo from file
def load_user_elo():
    with open('user_elo.json', 'r') as f:
        return json.load(f)


@bot.command(pass_context=True)
@has_permissions(manage_roles=True)
async def update_elo(ctx, user: Option(discord.User, required=True, description="User you want to update the elo for"), 
                     placement: Option(int, min_value=1, max_value=10, required=True, description="placement of the user"),
                     min_elo: Option(int, required=True, description="Person with the least amount of elo in the match"),
                     max_elo: Option(int, required=True, description="Person with the most elo in the match")):

    user_elo = load_user_elo()

    user_found = False
    for current_user in user_elo['users']:
        if current_user["id"] == user.id:
            user_current_elo = current_user['elo']  # Set the 'elo' key to a single value
            user_found = True
            break

    if not user_found:
        await ctx.respond(f"{user.mention} is not in the ELO database. setting to default 1000", ephemeral=True)
        user_current_elo = 1000

    if min_elo > max_elo:
        embed = discord.Embed(
        title=f"oops!",
        description="Minimum ELO should be less than or equal to Maximum ELO.",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    # Calculate new ELO based on placement

    elo = calculate_elo(user_current_elo, placement, max_elo, min_elo)


    # Update user_elo
    user_found = False
    for current_user in user_elo['users']:
        if current_user['id'] == user.id:
            current_user['elo'] = elo  # Set the 'elo' key to a single value
            user_found = True
            break

    if not user_found:
        user_elo['users'].append({
            'id': user.id,
            'elo': elo
        })

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)

    embed = discord.Embed(
    title=f"{user.name}'s ELO changed",
    description=f"**New ELO: {elo}**",
    color=discord.Color.green()
    )
    embed.set_thumbnail(url=user.avatar.url)
    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ctx.author} updated {user}'s elo\nplacement: {placement} \nmin_elo: {min_elo}\nmax_elo: {max_elo}")
    await ctx.respond(embed=embed)


@update_elo.error
async def timeouterror(ctx, error):
    if isinstance(error, MissingPermissions):
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**You need manage roles permissions to run this command**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        raise error


# Command to ping the bot
@bot.command(description="ping the bot")
async def ping(ctx):
    await ctx.respond("pong!", ephemeral=True)



def get_timezone_by_abbreviation(abbreviation):
    try:
        return pytz.timezone(abbreviation)
    except pytz.UnknownTimeZoneError:
        return None



# Define a simple cog for scheduling
class ScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule_loop.start()  

    def cog_unload(self):
        self.schedule_loop.stop()

    @tasks.loop(seconds=60)
    async def schedule_loop(self):
        # Get the current time in UTC
        current_time_utc = datetime.datetime.now(datetime.timezone.utc)

        with open('user_elo.json', encoding='utf-8') as w:
            try:
                user_elo = json.load(w)
            except ValueError:
                user_elo = {}
                user_elo['events'] = []

        events = user_elo.get('events', [])

        # Check if the current time is close to any scheduled event
        for event in events:
            event_name = event['name']
            event_time = event['time']
            event_zone_str = event['timezone']
            channel_id = event['channel']

            # Convert event time to datetime with timezone

            event_zone = pytz.timezone(event_zone_str)
            event_time_obj = event_zone.localize(datetime.datetime.strptime(event_time, "%Y-%m-%d %H:%M"))

            # Check if the current time is within a certain range of the scheduled time (e.g., 5 minutes)
            time_difference = (event_time_obj - current_time_utc).total_seconds() / 60
            if abs(time_difference) < 5:
                # Delete the completed event
                events.remove(event)

                # Save the updated user_elo data to the file
                with open('user_elo.json', 'w') as w:
                    json.dump(user_elo, w)

                # Use self.channel_id to fetch the channel dynamically
                channel = await self.bot.fetch_channel(channel_id)
                if channel:
                    embed = discord.Embed(
                    title=f"Time for an Event!",
                    description=f"**{event_name} is happening soon!**",
                    color=discord.Color.green()
                    )
                    
                    await channel.send("<@1190738155956080780>", embed=embed)

# Add the cog to the bot
bot.add_cog(ScheduleCog(bot))


@bot.command(pass_context=True, description="Use me for correct syntax!")
@has_permissions(manage_channels=True)
async def schedule_help(ctx, month: Option(str, choices=months, required=True, description="Month"), 
                    day: Option(int, min_value=1, max_value=32, required=True, description="Day"), 
                    year: Option(int, required=True, description="Year"), 
                    hour:Option(int, min_value=1, max_value=12, required=True, description="Hour"),
                    minute: Option(int, min_value=0, max_value=59, required=True, description="Minute"),
                    td: Option(str, choices=["AM", "PM"], required=True, description="Time of Day")):

    hour, minute = standard_to_military(hour=hour, minute=minute, period=td)

    month = [i for i,x in enumerate(months) if x == month]

    #clip = discord.ui.Button(label="Copy! (PC)", style=discord.ButtonStyle.green, emoji="📋")
    mobile = discord.ui.Button(label="Mobile Mode", style=discord.ButtonStyle.green, emoji="📱")


    view = discord.ui.View()
    #view.add_item(clip)
    view.add_item(mobile)


    embed = discord.Embed(
    title=f"Copy n' Paste!",
    description=f"Your event time! \n `{year}-{month[0]+1}-{day} {hour}:{minute}`",
    color=discord.Color.green()
    )
    await ctx.respond(embed=embed, view=view, ephemeral=True)

    #async def copy(interaction):
        #clipboard.copy(f'{year}-{month[0]+1}-{day} {hour}:{minute}')
        #await interaction.response.send_message('Copied!', ephemeral=True)
    
    async def copy_mobile(interaction):
        await interaction.response.send_message(f'{year}-{month[0]+1}-{day} {hour}:{minute}', ephemeral=True)

    #clip.callback = copy
    mobile.callback = copy_mobile

@bot.command(pass_context=True, description="Add an event!")
@has_permissions(manage_channels=True)
async def add_event(ctx, event_name: Option(str, required=True, description="Name of the event"), 
                    event_time: Option(str, required=True, description="Time of the event, use /schedule_help for help."), 
                    time_zone: Option(str, required=True, description="Event time zone, use /schedule_help for help."), 
                    channel:Option(discord.TextChannel, required=True, description="Channel I will send the announcement to.")):
    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)

    # Check if the event name already exists
    for event in user_elo['events']:
        if event['name'] == event_name:
            await ctx.send(f"Event '{event_name}' already exists.")
            return

    # Determine the channel to send the event message
    channel_status = await bot.fetch_channel(channel.id)

    date_format = "%Y-%m-%d %H:%M"
    
    # Check if the timezone in the string is a valid timezone
    timezone_str = time_zone[-5:]
    if timezone_str in pytz.all_timezones:
        pass
    else:
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**Did you use the right time zone? Use /schedule_help for syntax!**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    try:
        datetime.datetime.strptime(event_time, date_format)

    except ValueError:
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**Did you use the right time syntax? Use /schedule_help for syntax!**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return


    print(channel_status)

    # Add the new event to the events list
    user_elo['events'].append({
        'name': event_name,
        'time': event_time,
        'timezone': time_zone,
        'channel': channel.id
    })

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)

    embed = discord.Embed(
    title=f"Event added!",
    description=f"**An announcement will be sent to <#{channel.id}> at {event_time} {time_zone} for {event_name}**",
    color=discord.Color.green()
    )
    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ctx.author} added an event {event_name}")
    await ctx.respond(embed=embed, ephemeral=True)


@add_event.error
async def timeouterror(ctx, error):
    if isinstance(error, MissingPermissions):
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**You need manage channels permissions to run this command**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)

    if isinstance(error, discord.errors.ApplicationCommandInvokeError):
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**something went wrong! Do I have channel permissions?**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)

    else:
        raise error

# Define a command to read events
@bot.command(description="View events!")
async def events(ctx):
    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)

    events = user_elo.get('events', [])
    if not events:
        embed = discord.Embed(
        title=f"No events found!",
        color=discord.Color.yellow()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    event_list = "\n\n".join([f"**{event['name']}**\n{military_to_standard(event['time'])} {event['timezone']}" for event in events])
    embed = discord.Embed(
    title=f"Upcoming Events!",
    description=event_list,
    color=discord.Color.light_grey()
    )
    await ctx.respond(embed=embed, ephemeral=True)

async def get_events(ctx):
    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)
        events = user_elo["events"]
    
    event_names = [str(event["name"]) for event in events]
    return event_names



@bot.command()
@has_permissions(manage_channels=True)
async def remove_event(ctx,
                event: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_events))):
    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)

    events = user_elo.get('events', [])
    if not events:
        embed = discord.Embed(
            title=f"No events found!",
            color=discord.Color.yellow()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

    filtered_events = [evt for evt in events if evt['name'] != event]
    user_elo['events'] = filtered_events
    with open('user_elo.json', 'w', encoding='utf-8') as w:
        json.dump(user_elo, w)

    embed = discord.Embed(
        title=f"Event {event} removed!",
        color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ctx.author} deleted event {event}")

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)


@remove_event.error
async def timeouterror(ctx, error):
    if isinstance(error, MissingPermissions):
        embed = discord.Embed(
        title=f"Oops!",
        description=f"**You need manage channels permissions to run this command**\n*Error? Contact @FormalStatic*",
        color=discord.Color.red()
        )
        await ctx.respond(embed=embed, ephemeral=True)
    else:
        raise error

# Command to set elo for a user (requires manage_roles and ban_members permissions)
@bot.command(pass_context=True)
@has_permissions(manage_roles=True)
async def elo_set(ctx, user: discord.User, elo: int):
    author = ctx.author

    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)


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
        if current_user['id'] == user.id:
            current_user['elo'] = elo  # Set the 'elo' key to a single value
            user_found = True
            break

    if not user_found:
        user_elo['users'].append({
            'id': user.id,
            'elo': elo
        })

    # Save the updated user_elo data to the file
    with open('user_elo.json', 'w') as w:
        json.dump(user_elo, w)

    webhook.send(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ctx.author} set {user}'s elo to {elo}")


# Command to check elo for a user
@bot.command(pass_context=True)
async def elo(ctx, user: Option(discord.User, required=False)):
    with open('user_elo.json', encoding='utf-8') as w:
        user_elo = json.load(w)
    if user == None:
        user_id = ctx.author.id
        user = ctx.author
    else:
        user_id = user.id
    for current_user in user_elo['users']:
        if user_id == current_user['id']:
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
