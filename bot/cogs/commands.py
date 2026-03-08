from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from bot.database import get_member_activity, get_top_mia_sessions

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


def _format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds} second(s)"

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

    return ", ".join(parts)


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

        activity = await get_member_activity(
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


    @commands.command(name="topmia")
    async def top_mia(self, ctx: commands.Context, n: int = 10) -> None:
        """Show the top N longest M.I.A. sessions in this guild."""
        if n < 1 or n > 50:
            await ctx.send("Please provide a number between 1 and 50.")
            return

        rows = await get_top_mia_sessions(self.bot.pool, ctx.guild.id, n)
        if not rows:
            await ctx.send("No M.I.A. session data recorded yet.")
            return

        lines = [f"🏆 **Top {n} Longest M.I.A. Sessions**"]
        for i, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["member_id"])
            name = member.display_name if member else f"<Unknown:{row['member_id']}>"
            duration = _format_duration(row["duration"])
            suffix = " *(ongoing)*" if row["ended_at"] is None else ""
            lines.append(f"{i}. **{name}** — {duration}{suffix}")

        chunks, current = [], ""
        for line in lines:
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) > 2000:
                chunks.append(current)
                current = line
            else:
                current = candidate
        if current:
            chunks.append(current)
        for chunk in chunks:
            await ctx.send(chunk)

    @top_mia.error
    async def top_mia_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.BadArgument):
            await ctx.send("Usage: `!topmia [N]` — N must be a whole number between 1 and 50.")
        else:
            raise error

    @mia.error
    async def mia_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Usage: `!mia <username or @mention>`")
        else:
            raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Commands(bot))
