import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
import io
import json
import os
import yt_dlp
import asyncio
from collections import deque

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af "aresample=48000,bass=g=2,treble=g=-2,acompressor=threshold=-25dB:ratio=3:attack=10:release=100,alimiter=limit=0.95,volume=1.3"'
}

YDL_OPTIONS = {
    'format': 'bestaudio[acodec=opus]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

VOLUME_DEFAULT = 0.65 

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True          

bot = commands.Bot(command_prefix='!', intents=intents)

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_channels.json')

def load_log_channels():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                return {int(k): v for k, v in data.items()}
        except Exception as e:
            print(f"❌ Lỗi đọc file log_channels.json: {e}")
    return {}

def save_log_channels():
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(log_channels, f, indent=2)
    except Exception as e:
        print(f"[{get_current_time()}] ❌ Lỗi lưu file log_channels.json: {e}")
log_channels = load_log_channels()

music_queues = {}

def get_music_state(guild_id):
    """Lấy hoặc tạo trạng thái nhạc cho một server."""
    if guild_id not in music_queues:
        music_queues[guild_id] = {
            "queue": deque(),
            "now_playing": None,
        }
    return music_queues[guild_id]

def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

async def search_yt(query):
    """Tìm kiếm/trích xuất audio từ YouTube (chạy trong thread riêng để không block bot)."""
    loop = asyncio.get_event_loop()

    def _extract():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                if not info['entries']:
                    return None
                info = info['entries'][0]
            return {
                'title': info.get('title', 'Không rõ'),
                'url': info['url'],
                'webpage_url': info.get('webpage_url', ''),
            }

    try:
        return await loop.run_in_executor(None, _extract)
    except Exception:
        return None

def play_next(guild):
    """Phát bài tiếp theo trong hàng đợi. Nếu hết queue thì idle (KHÔNG rời kênh)."""
    state = get_music_state(guild.id)
    voice_client = guild.voice_client

    if not voice_client or not voice_client.is_connected():
        state["now_playing"] = None
        return

    if len(state["queue"]) == 0:
        state["now_playing"] = None
        return

    next_song = state["queue"].popleft()
    state["now_playing"] = next_song

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS),
        volume=VOLUME_DEFAULT
    )

    def after_playing(error):
        if error:
            print(f"[{get_current_time()}] ❌ Lỗi phát nhạc tại {guild.name}: {error}")
        bot.loop.call_soon_threadsafe(play_next, guild)

    voice_client.play(source, after=after_playing)

async def ensure_voice(interaction):
    """Đảm bảo bot ở trong voice channel của người dùng. Trả về VoiceClient hoặc None."""
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send("❌ Bạn cần vào một kênh thoại trước!")
        return None

    target_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await target_channel.connect()
    elif voice_client.channel.id != target_channel.id:
        await voice_client.move_to(target_channel)

    return voice_client

async def send_to_log(guild, content=None, embed=None, file=None):
    if guild.id in log_channels:
        channel = bot.get_channel(log_channels[guild.id])
        if channel:
            try:
                if file:
                    await channel.send(content=content, embed=embed, file=file)
                else:
                    await channel.send(content=content, embed=embed)
            except Exception as e:
                print(f"[{get_current_time()}] ❌ Lỗi gửi log: {e}")

@bot.event
async def on_ready():
    print(f'[{get_current_time()}] ✅ Bot đã hoạt động với tên: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"[{get_current_time()}] 🔄 Đã đồng bộ {len(synced)} lệnh slash (/)")
    except Exception as e:
        print(f"[{get_current_time()}] ❌ Lỗi đồng bộ lệnh slash: {e}")

    if not update_status.is_running():
        update_status.start()

@tasks.loop(minutes=5)
async def update_status():
    server_count = len(bot.guilds)
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=f"trên {server_count} server"
    )
    await bot.change_presence(activity=activity)
    print(f"[{get_current_time()}] 🎮 Cập nhật trạng thái: Đang chơi trên {server_count} server")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    time_str = get_current_time()
    attachment_info = f" [Có {len(message.attachments)} file]" if message.attachments else ""
    print(f"[{time_str}] [CHAT] [#{message.channel.name}] {message.author.name}: {message.content}{attachment_info}")
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    time_str = get_current_time()
    print(f"[{time_str}] [XÓA] [#{message.channel.name}] {message.author.name} vừa xóa: {message.content}")

    text_content = f"`[{time_str}]` 🗑️ **{message.author.name}** vừa xóa tin nhắn:\n> {message.content}"
    files = []
    for attachment in message.attachments:
        try:
            files.append(await attachment.to_file())
        except: pass
    await message.channel.send(content=text_content, files=files)

    log_text = f"`[{time_str}]` 🗑️ **{message.author.name}** đã xóa một tin nhắn trong <#{message.channel.id}>:\n> {message.content}"
    await send_to_log(message.guild, content=log_text)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    time_str = get_current_time()
    
    if before.channel is None and after.channel is not None:
        print(f"[{time_str}] [VOICE] {member.name} JOIN {after.channel.name}")
        try:
            await after.channel.send(f"`[{time_str}]` 👋 **{member.display_name}** đã tham gia kênh thoại!")
        except: pass
        await send_to_log(member.guild, f"`[{time_str}]` 🎤 **{member.name}** đã tham gia kênh thoại **{after.channel.name}**")

    elif before.channel is not None and after.channel is None:
        print(f"[{time_str}] [VOICE] {member.name} LEAVE {before.channel.name}")
        await send_to_log(member.guild, f"`[{time_str}]` 🚪 **{member.name}** đã rời khỏi kênh thoại **{before.channel.name}**")

    elif before.channel is not None and after.channel is not None and before.channel != after.channel:
        print(f"[{time_str}] [VOICE] {member.name} MOVED from {before.channel.name} to {after.channel.name}")
        try:
            await after.channel.send(f"`[{time_str}]` 👋 **{member.display_name}** đã chuyển đến kênh thoại này!")
        except: pass
        await send_to_log(member.guild, f"`[{time_str}]` 🔀 **{member.name}** đã bị chuyển/tự chuyển từ **{before.channel.name}** sang **{after.channel.name}**")

@bot.event
async def on_member_join(member):
    time_str = get_current_time()
    print(f"[{time_str}] [SERVER] {member.name} đã THAM GIA server")
    await send_to_log(member.guild, f"`[{time_str}]` 🌟 **{member.name}** vừa tham gia Server!")

@bot.event
async def on_member_remove(member):
    time_str = get_current_time()
    print(f"[{time_str}] [SERVER] {member.name} đã THOÁT server")
    await send_to_log(member.guild, f"`[{time_str}]` 💔 **{member.name}** đã rời khỏi Server!")

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        time_str = get_current_time()
        old_name = before.nick if before.nick else before.name
        new_name = after.nick if after.nick else after.name
        
        print(f"[{time_str}] [ĐỔI TÊN] {before.name}: '{old_name}' -> '{new_name}'")
        
        embed = discord.Embed(title="📝 Cập nhật Biệt danh", color=discord.Color.blue())
        embed.description = f"`[{time_str}]` **{before.name}** đã đổi tên."
        embed.add_field(name="Từ", value=old_name, inline=True)
        embed.add_field(name="Thành", value=new_name, inline=True)
        
        await send_to_log(after.guild, embed=embed)

@bot.tree.command(name="setlog", description="Thiết lập kênh hiển thị Full Log")
@app_commands.describe(channel="Chọn kênh text để làm kênh log")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Cần quyền Quản trị viên!", ephemeral=True)
        return
        
    log_channels[interaction.guild.id] = channel.id
    save_log_channels()
    print(f"[{get_current_time()}] [SYSTEM] Đã set kênh log thành #{channel.name}")
    await interaction.response.send_message(f"✅ Đã thiết lập kênh log thành {channel.mention}!", ephemeral=True)

@bot.tree.command(name="createrole", description="Tạo một Role mới với tên và màu sắc")
@app_commands.describe(name="Tên role muốn tạo", color_hex="Mã màu Hex (Ví dụ: #ff0000 cho màu đỏ)")
async def createrole(interaction: discord.Interaction, name: str, color_hex: str = "#99aab5"):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Bạn không có quyền Quản lý Role!", ephemeral=True)
        return

    try:
        color = discord.Color.from_str(color_hex)
        role = await interaction.guild.create_role(name=name, color=color, reason=f"Tạo bởi {interaction.user}")
        
        time_str = get_current_time()
        print(f"[{time_str}] [ROLE] {interaction.user.name} đã tạo role '{name}' với màu {color_hex}")
        await interaction.response.send_message(f"✅ Đã tạo thành công role {role.mention}!", ephemeral=True)
        await send_to_log(interaction.guild, f"`[{time_str}]` 🆕 **{interaction.user.name}** đã tạo role mới: **{name}** ({color_hex})")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}. Đảm bảo mã màu đúng định dạng #ffffff", ephemeral=True)

@bot.tree.command(name="addrole", description="Cấp Role cho một thành viên")
@app_commands.describe(member="Người được cấp", role="Role muốn cấp")
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ Bạn không có quyền Quản lý Role!", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        time_str = get_current_time()
        print(f"[{time_str}] [ROLE] {interaction.user.name} đã cấp role '{role.name}' cho {member.name}")
        await interaction.response.send_message(f"✅ Đã cấp role {role.mention} cho **{member.display_name}**!", ephemeral=True)
        await send_to_log(interaction.guild, f"`[{time_str}]` 🎖️ **{interaction.user.name}** đã cấp role {role.mention} cho **{member.name}**")
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}. Hãy đảm bảo Role của Bot nằm cao hơn Role cần cấp.", ephemeral=True)

@bot.tree.command(name="nuke", description="Xóa hàng loạt tin nhắn (Max 150) và Backup vào Log")
@app_commands.describe(amount="Số lượng tin nhắn cần xóa (1-150)")
async def nuke(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ Bạn không có quyền quản lý tin nhắn!", ephemeral=True)
        return
        
    if amount < 1 or amount > 150:
        await interaction.response.send_message("❌ Số lượng không hợp lệ. Vui lòng nhập từ 1 đến 150!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        deleted_messages = await interaction.channel.purge(limit=amount)
        time_str = get_current_time()
        
        print(f"[{time_str}] [NUKE] {interaction.user.name} đã xóa {len(deleted_messages)} tin nhắn ở #{interaction.channel.name}")
        await interaction.followup.send(f"✅ Đã dọn dẹp thành công **{len(deleted_messages)}** tin nhắn!", ephemeral=True)
        
        if len(deleted_messages) > 0:
            deleted_messages.reverse() 
            
            backup_text = f"--- BẢN SAO LƯU TIN NHẮN (Lệnh /nuke) ---\n"
            backup_text += f"Người thực hiện: {interaction.user.name}\n"
            backup_text += f"Kênh xóa: #{interaction.channel.name}\n"
            backup_text += f"Thời gian thực hiện: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            backup_text += f"Tổng số tin nhắn: {len(deleted_messages)}\n"
            backup_text += "-" * 50 + "\n\n"
            
            for msg in deleted_messages:
                msg_time = msg.created_at.strftime("%d/%m/%Y %H:%M:%S")
                backup_text += f"[{msg_time}] {msg.author.name}: {msg.content}\n"
                if msg.attachments:
                    for att in msg.attachments:
                        backup_text += f"    -> Đính kèm: {att.url}\n"
            
            file_bytes = io.BytesIO(backup_text.encode('utf-8'))
            backup_file = discord.File(file_bytes, filename=f"Backup_Nuke_{interaction.channel.name}.txt")
            
            log_msg = f"`[{time_str}]` 💣 **{interaction.user.name}** đã `/nuke` **{len(deleted_messages)}** tin nhắn trong <#{interaction.channel.id}>. File sao lưu đính kèm bên dưới:"
            await send_to_log(interaction.guild, content=log_msg, file=backup_file)

    except Exception as e:
        await interaction.followup.send(f"❌ Đã xảy ra lỗi khi xóa tin nhắn: {e}", ephemeral=True)

@bot.command(name='av')
async def avatar(ctx, member: discord.Member = None):
    time_str = get_current_time()
    member = member or ctx.author
    print(f"[{time_str}] [COMMAND] {ctx.author.name} đã dùng lệnh !av xem avatar của {member.name}")

    embed = discord.Embed(title=f"Avatar của {member.display_name}", color=discord.Color.random())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.tree.command(name="play", description="Phát nhạc từ YouTube (tìm kiếm hoặc dán link)")
@app_commands.describe(query="Link YouTube hoặc tên bài hát")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()

    voice_client = await ensure_voice(interaction)
    if voice_client is None:
        return

    song = await search_yt(query)
    if song is None:
        await interaction.followup.send("❌ Không tìm thấy bài hát hoặc không thể trích xuất audio.")
        return

    song['requester'] = interaction.user.display_name
    state = get_music_state(interaction.guild_id)
    time_str = get_current_time()

    if voice_client.is_playing() or voice_client.is_paused():
        state["queue"].append(song)
        position = len(state["queue"])
        print(f"[{time_str}] [MUSIC] {interaction.user.name} thêm vào hàng đợi: {song['title']}")
        await interaction.followup.send(
            f"📋 **Đã thêm vào hàng đợi #{position}:** [{song['title']}]({song['webpage_url']}) "
            f"(yêu cầu bởi {song['requester']})"
        )
    else:
        state["now_playing"] = song
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS),
            volume=VOLUME_DEFAULT
        )

        def after_playing(error):
            if error:
                print(f"[{get_current_time()}] ❌ Lỗi phát nhạc: {error}")
            bot.loop.call_soon_threadsafe(play_next, interaction.guild)

        voice_client.play(source, after=after_playing)
        print(f"[{time_str}] [MUSIC] {interaction.user.name} phát: {song['title']}")
        await interaction.followup.send(
            f"🎶 **Đang phát:** [{song['title']}]({song['webpage_url']}) "
            f"(yêu cầu bởi {song['requester']})"
        )

@bot.tree.command(name="skip", description="Bỏ qua bài hát hiện tại")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("❌ Hiện không có bài nào đang phát.", ephemeral=True)
        return

    current = get_music_state(interaction.guild_id).get("now_playing")
    title = current['title'] if current else 'bài hiện tại'

    voice_client.stop()
    print(f"[{get_current_time()}] [MUSIC] {interaction.user.name} đã skip: {title}")
    await interaction.response.send_message(f"⏭️ Đã bỏ qua **{title}**.")

@bot.tree.command(name="stop", description="Dừng phát nhạc và xóa hàng đợi (bot vẫn ở trong kênh)")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    state = get_music_state(interaction.guild_id)

    state["queue"].clear()
    state["now_playing"] = None

    if voice_client and voice_client.is_playing():
        voice_client.stop()

    print(f"[{get_current_time()}] [MUSIC] {interaction.user.name} đã dừng phát nhạc")
    await interaction.response.send_message("⏹️ Đã dừng phát nhạc và xóa hàng đợi.")

@bot.tree.command(name="queue", description="Xem danh sách bài hát trong hàng đợi")
async def queue(interaction: discord.Interaction):
    state = get_music_state(interaction.guild_id)
    now = state["now_playing"]

    if not now and len(state["queue"]) == 0:
        await interaction.response.send_message("📭 Hàng đợi trống. Dùng `/play` để thêm bài hát!")
        return

    lines = []
    if now:
        lines.append(f"🎶 **Đang phát:** [{now['title']}]({now['webpage_url']}) — {now['requester']}")

    for i, song in enumerate(state["queue"], start=1):
        lines.append(f"`{i}.` [{song['title']}]({song['webpage_url']}) — {song['requester']}")
        if i >= 20:
            remaining = len(state["queue"]) - 20
            if remaining > 0:
                lines.append(f"*...và {remaining} bài nữa*")
            break

    await interaction.response.send_message("\n".join(lines))

@bot.tree.command(name="volume", description="Chỉnh âm lượng phát nhạc (0-100)")
@app_commands.describe(level="Mức âm lượng từ 0 đến 100")
async def volume(interaction: discord.Interaction, level: int):
    voice_client = interaction.guild.voice_client

    if not voice_client or not voice_client.source:
        await interaction.response.send_message("❌ Hiện không có bài nào đang phát.", ephemeral=True)
        return

    if level < 0 or level > 100:
        await interaction.response.send_message("❌ Âm lượng phải từ 0 đến 100!", ephemeral=True)
        return

    voice_client.source.volume = level / 100
    await interaction.response.send_message(f"🔊 Âm lượng đã chỉnh thành **{level}%**")

@bot.tree.command(name="leave", description="Bot rời khỏi kênh thoại")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client

    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("❌ Bot không ở trong kênh thoại nào.", ephemeral=True)
        return

    state = get_music_state(interaction.guild_id)
    state["queue"].clear()
    state["now_playing"] = None

    await voice_client.disconnect()

    if interaction.guild_id in music_queues:
        del music_queues[interaction.guild_id]

    print(f"[{get_current_time()}] [MUSIC] {interaction.user.name} đã yêu cầu bot rời kênh thoại")
    await interaction.response.send_message("👋 Đã rời khỏi kênh thoại và xóa hàng đợi.")


bot.run('Your_Bot_Token')
