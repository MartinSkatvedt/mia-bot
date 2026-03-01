from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot import database

OFFLINE_STATUSES = {discord.Status.offline, discord.Status.invisible}


def _format_timedelta(dt: datetime | None, label_if_none: str) -> str:
    if dt is None:
        return label_if_none

    now = datetime.now(tz=timezone.utc)
    delta = now - dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else now - dt

    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds} second(s) ago"

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes and not days:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    return ", ".join(parts) + " ago"


class Commands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="mia")
    async def mia(self, ctx: commands.Context, *, target: str) -> None:
        """Show inactivity report for a guild member."""
        member = None
        try:
            member = await commands.MemberConverter().convert(ctx, target)
        except commands.MemberNotFound:
            name = target.lstrip("@").lower()
            member = discord.utils.find(
                lambda m: m.name.lower() == name or m.display_name.lower() == name,
                ctx.guild.members,
            )

        if member is None:
            await ctx.send(f'Member "{target}" not found in this server.')
            return

        activity = await database.get_member_activity(
            self.bot.pool, ctx.guild.id, member.id
        )

        last_message_at = activity[0] if activity else None
        last_online_at = activity[1] if activity else None

        message_str = _format_timedelta(last_message_at, "Never recorded")

        if member.status not in OFFLINE_STATUSES:
            online_str = "Currently online"
        else:
            online_str = _format_timedelta(last_online_at, "Never recorded")

        display = member.name if not member.discriminator or member.discriminator == "0" else f"{member.name}#{member.discriminator}"
        report = (
            f"📋 **M.I.A. Report for {display}**\n"
            f"💬 Last message: {message_str}\n"
            f"🔴 Last online:  {online_str}"
        )
        await ctx.send(report)


    @mia.error
    async def mia_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `!mia <username or @mention>`")
        else:
            raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Commands(bot))
