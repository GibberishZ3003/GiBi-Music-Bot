import discord
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import google.generativeai as genai

GEMINI_API_KEY='AIzaSyCQa3D0ieRBUjkZ4X5GW4FZOY4PpaQPU58'
genai.configure(api_key=GEMINI_API_KEY)

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    queues = {}
    voice_clients = {}
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

    async def play_next(guild_id):
        try:
            if guild_id in queues and queues[guild_id]:
                player = queues[guild_id].pop(0)
                voice_clients[guild_id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id),
                                                                                                      client.loop))
            else:
                await voice_clients[guild_id].disconnect()
        except Exception as e:
            print(f"Error in play_next: {e}")

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    @client.event
    async def on_message(message):
        if message.content.startswith("?play"):
            try:
                voice_client = await message.author.voice.channel.connect()
                voice_clients[voice_client.guild.id] = voice_client
            except Exception as e:
                print(e)

            try:
                url = message.content.split()[1]
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                song = data['url']
                player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                voice_clients[message.guild.id].play(player)
            except Exception as e:
                print(e)

        if message.content.startswith("?pause"):
            try:
                voice_clients[message.guild.id].pause()
            except Exception as e:
                print(e)

        if message.content.startswith("?resume"):
            try:
                voice_clients[message.guild.id].resume()
            except Exception as e:
                print(e)

        if message.content.startswith("?stop"):
            try:
                voice_clients[message.guild.id].stop()
                await voice_clients[message.guild.id].disconnect()
            except Exception as e:
                print(e)

        if message.content.startswith("?queue"):
            try:
                link = message.content[len('?queue'):].strip()
                if message.guild.id not in queues:
                    queues[message.guild.id] = []

                # Fetch song URL
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                song_url = data['url']

                # Create AudioSource object
                player = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)

                queues[message.guild.id].append(player)
                await message.channel.send(f"Added {link} to the queue!")
            except Exception as e:
                print(f"Error in ?queue: {e}")

        if message.content.startswith('?next'):
            try:
                if message.guild.id in voice_clients and voice_clients[message.guild.id].is_playing():
                    voice_clients[message.guild.id].stop()
                    await message.channel.send('Skipping to next song...')
                    await play_next(message.guild.id)
                else:
                    await message.channel.send("No song is currently playing.")
            except Exception as e:
                print(f"Error in ?next: {e}")
                await message.channel.send("Error: Unable to skip to the next song.")

        if message.content.startswith("?ai"):
            question = message.content[len("?ai"):].strip()

            if not question:
                await message.channel.send("โปรดระบุคำถาม")
                return

            try:
                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content(question)
                if response and hasattr(response, 'text'):
                    response_text = response.text
                    for chunk in [response_text[i:i + 1900] for i in range(0, len(response_text), 1900)]:
                        await message.channel.send(chunk)
            except Exception as e:
                await message.channel.send(f"Error-เกิดปัญหาขัดข้อง: {e}")

    client.run(TOKEN)