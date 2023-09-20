from prometheus_client import start_http_server, Counter, Gauge
from discord.ext import commands, tasks
from discord import Interaction, InteractionType, AutoShardedClient
import psutil
import os

"""
需要紀錄的東西:
1. 群組數量
2. 成員數量
3. 指令使用次數
4. 指令使用時間
4. cpu使用率
5. ram使用率
6. 與discord的ping值
"""

guild_count = Gauge("guild_count", "Number of guilds")
channel_count = Gauge("channel_count", "Number of channels")
users_count = Gauge("users_count", "Number of users")
ping = Gauge("ping", "Ping to discord")
cpu_usage = Gauge("cpu_usage", "CPU usage")
ram_usage = Gauge("ram_usage", "RAM usage")
command_count = Counter("command_count", "Number of commands",["command"])
interaction_count = Counter(
    "interaction_count", "Number of interactions", ["type", "command"]
)
all_commands_count = Counter("all_commands_count", "Number of all commands")


class logcog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    def run_prometheus(self):
        start_http_server(8000)

    def sync_all_status(self):
        guild_count.set(len(self.bot.guilds))
        channel_count.set(len(list(self.bot.get_all_channels())))
        users_count.set(len(list(self.bot.get_all_members())))

    @tasks.loop(seconds=20)
    async def sync_sys_status(self):
        ping.set(round(self.bot.latency, 1))
        cpu_usage.set(psutil.cpu_percent(3))
        ram_usage.set(psutil.Process(os.getpid()).memory_percent())

    @commands.Cog.listener()
    async def on_ready(self):
        self.sync_all_status()
        self.sync_sys_status.start()
        self.run_prometheus()

    @commands.Cog.listener()
    async def on_command(self, ctx):
        command_count.labels(ctx.command.name).inc()
        all_commands_count.inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        cmdname = None
        if interaction.type == InteractionType.application_command:
            cmdname = interaction.command.name
        interaction_count.labels(
            interaction.type.name, cmdname
        ).inc()
        all_commands_count.inc()

    @commands.Cog.listener()
    async def on_guide_join(self, guild):
        self.sync_guild_status()

    @commands.Cog.listener()
    async def on_guide_remove(self, guild):
        self.sync_guild_status()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        users_count.inc()

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        users_count.dec()
