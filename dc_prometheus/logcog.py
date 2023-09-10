from prometheus_client import start_http_server, Counter, Gauge
from discord.ext import commands, tasks
from discord import Interaction, InteractionType, AutoShardedClient

class logcog(commands.Cog):

    def __init__(self,bot) -> None:
        self.bot=bot


    def allcommands(self):
        commands = []
        for command in self.bot.commands:
            commands.append(command.name)
        return commands
    
    @commands.Cog.listener()
    async def on_command(self,ctx):
        ...