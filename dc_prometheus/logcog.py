from prometheus_client import start_http_server, Counter, Gauge
from discord.ext import commands, tasks
from discord import Interaction, InteractionType, AutoShardedClient, Status
import psutil
import os
import logging
from enum import Enum

log = logging.getLogger("prometheus")

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
users_online = Gauge("users_online", "Number of users online")
ping = Gauge("ping", "Ping to discord")
cpu_usage = Gauge("cpu_usage", "CPU usage")
ram_usage = Gauge("ram_usage", "RAM usage")
command_count = Counter("command_count", "Number of commands", ["command"])
interaction_count = Counter(
    "interaction_count", "Number of interactions", ["type", "command"]
)
all_commands_count = Counter("all_commands_count", "Number of all commands")
message_count = Counter("message_count", "Number of messages", ["guild", "user"])

class lib(Enum):
    discordpy = "Discord.py"
    pycord = "Pycord"

class logcog(commands.Cog):
    def __init__(self, bot: commands.Bot, port: int = 8000) -> None:
        """
        Args:
            bot: discord bot
            port (int, optional): prometheus server port. Defaults is 8000
        """
        self.bot = bot
        self.lib = self.check_library(bot)
        self.running = False
        self.port = port

    def check_library(bot) -> lib:
        if hasattr(bot, 'application_commands'):
            return lib.pycord
        elif hasattr(bot, 'tree'):
            return lib.discordpy
        else:
            return lib.discordpy

    def run_prometheus(self) -> None:
        try:
            start_http_server(self.port)
        except OSError:
            log.warning(
                f"Port {self.port} is already in use, try {self.port+1} instead"
            )
            self.port += 1
            self.run_prometheus()
            return
        log.info(f"Prometheus server started on port {self.port}")
        self.running = True

    def sync_all_status(self) -> None:
        guild_count.set(len(self.bot.guilds))
        channel_count.set(len(list(self.bot.get_all_channels())))
        users_count.set(len(list(self.bot.get_all_members())))
        users_online.set(
            len(
                list(
                    filter(
                        lambda m: m.status != Status.offline, self.bot.get_all_members()
                    )
                )
            )
        )

    @tasks.loop(seconds=20)
    async def sync_sys_status(self) -> None:
        ping.set(round(self.bot.latency, 1))
        cpu_usage.set(psutil.cpu_percent(3))
        ram_usage.set(psutil.Process(os.getpid()).memory_percent())

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.sync_all_status()
        self.sync_sys_status.start()
        if not self.running:
            self.run_prometheus()

    @commands.Cog.listener()
    async def on_command(self, ctx) -> None:
        command_count.labels(ctx.command.name).inc()
        all_commands_count.inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        cmdname = None
        if self.lib == lib.discordpy:
            if interaction.type == InteractionType.application_command:
                cmdname = interaction.command.name
        else:
            if interaction.type == InteractionType.application_command:
                cmdname = interaction.data.name
        interaction_count.labels(interaction.type.name, cmdname).inc()
        all_commands_count.inc()

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.guild:
            message_count.labels(message.guild.id, message.author.id).inc()
        else:
            message_count.labels(0, message.author.id).inc()

    @commands.Cog.listener()
    async def on_guild_join(self, guild) -> None:
        self.sync_all_status()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild) -> None:
        self.sync_all_status()

    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        users_count.inc()

    @commands.Cog.listener()
    async def on_member_remove(self, member) -> None:
        users_count.dec()
