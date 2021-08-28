from discord.ext import commands
import discord
from aiohttp import request
import asyncio

from .utils.DataBase.tag import Tag

def setup(bot):
    bot.add_cog(TagCommands(bot=bot))

class TagCommands(commands.Cog, name="Tags"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name: lambda inp: inp.lower()):
        """Main tag group."""

        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)
        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)
        await ctx.send("{}".format(tag.content))
        await self.bot.db.execute("UPDATE tags SET uses = uses + 1 WHERE guild_id = $1 AND name = $2",
                                  ctx.guild.id, name)

    @tag.command()
    async def info(self, ctx, *, name: lambda inp: inp.lower()):
        """Get information regarding the specified tag."""
        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)

        author = self.bot.get_user(tag.creator_id)
        author = str(author) if isinstance(author, discord.User) else "(ID: {})".format(tag.creator_id)
        text = "Tag: {name}\n\n```prolog\nCreator: {author}\n   Uses: {uses}\n```"\
            .format(name=name, author=author, uses=tag.uses)
        await ctx.send(text)

    @tag.command()
    @commands.check_any(commands.has_permissions(administrator=True))
    async def create(self, ctx, name: lambda inp: inp.lower(), *, content: str):
        """Create a new tag."""
        name = await commands.clean_content().convert(ctx=ctx, argument=name)
        content = await commands.clean_content().convert(ctx=ctx, argument=content)
        user_id = ctx.author.id

        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)
        if tag is not None:
            return await ctx.send('A tag with that name already exists.')

        tag = Tag(bot=self.bot, guild_id=ctx.guild.id,
                  creator_id=ctx.author.id, name=name, content=content)
        await tag.post()
        await ctx.send('You have successfully created your tag.')

    @tag.command()
    async def list(self, ctx, member: commands.MemberConverter = None):
        """List your existing tags."""
        member = member or ctx.author
        query = """SELECT name FROM tags WHERE guild_id = $1 AND creator_id = $2 ORDER BY name, uses"""
        records = await self.bot.db.fetch(query, ctx.guild.id, member.id)
        if not records:
            return await ctx.send('No tags found.')

        await ctx.send(
            f"**{len(records)} tags by {'you' if member == ctx.author else str(member)} found on this server.**"
        )

        pager = commands.Paginator()

        for record in records:
            pager.add_line(line=record["name"])

        for page in pager.pages:
            await ctx.send(page)

    @tag.command()
    @commands.cooldown(1, 3600 * 24, commands.BucketType.user)
    async def all(self, ctx: commands.Context):
        """List all existing tags alphabetically ordered and sends them in DMs."""
        records = await self.bot.db.fetch(
            """SELECT name FROM tags WHERE guild_id = $1 ORDER BY name""",
            ctx.guild.id
        )

        if not records:
            return await ctx.send("This server doesn't have any tags.")

        try:
            await ctx.author.send(f"***{len(records)} tags found on this server.***")
        except discord.Forbidden:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("Could not dm you...", delete_after=10)

        pager = commands.Paginator()

        for record in records:
            pager.add_line(line=record["name"])

        for page in pager.pages:
            await asyncio.sleep(1)
            await ctx.author.send(page)

        await ctx.send("Tags sent in DMs.")

    @tag.command()
    async def edit(self, ctx, name: lambda inp: inp.lower(), *, content: str):
        """Edit a tag"""
        content = await commands.clean_content().convert(ctx=ctx, argument=content)

        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)

        if tag.creator_id != ctx.author.id:
            return await ctx.send('You don\'t have permission to do that.')

        await tag.update(content=content)
        await ctx.send('You have successfully edited your tag.')

    @tag.command()
    async def delete(self, ctx, *, name: lambda inp: inp.lower()):
        """Delete an existing tag."""
        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)

        if tag.creator_id != ctx.author.id:
            return await ctx.send('You don\'t have permission to do that.')

        await tag.delete()
        await ctx.send('You have successfully deleted your tag.')

    @tag.command()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def search(self, ctx, *, term: str):
        """Search for a tag given a search term."""
        # Test this.
        query = """SELECT name FROM tags WHERE guild_id = $1 AND name LIKE % $2 % LIMIT 10"""
        records = await self.bot.db.fetch(query, ctx.guild.id, term)

        if not records:
            return await ctx.send("No tags found that has the term in it's name", delete_after=10)
        count = "Maximum of 10" if len(records) == 10 else len(records)
        records = "\n".join([record["name"] for record in records])

        await ctx.send(f"**{count} tags found with search term on this server.**```\n{records}\n```")

        #Add a rename and append feature later maybe

    async def rename(self, ctx, name: lambda inp: inp.lower(), *, new_name: lambda inp: inp.lower()):
        """Rename a tag."""

        new_name = await commands.clean_content().convert(ctx=ctx, argument=new_name)

        tag = await self.bot.db.get_tag(guild_id=ctx.guild.id, name=name)

        if tag is None:
            await ctx.message.delete(delay=10.0)
            message = await ctx.send('Could not find a tag with that name.')
            return await message.delete(delay=10.0)

        if tag.creator_id != ctx.author.id:
            return await ctx.send('You don\'t have permission to do that.')

        await tag.rename(new_name=new_name)
        await ctx.send('You have successfully renamed your tag.')
