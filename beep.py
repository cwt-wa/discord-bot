# bot.py
import threading
import os
import re
import threading
import subprocess
import discord
from dotenv import load_dotenv
import json
import requests
from sseclient import SSEClient
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SCRIPT = os.getenv('SCRIPT') or './'
LISTEN = os.getenv('LISTEN') == "1"
CHANNEL = os.getenv('CHANNEL')
client = discord.Client()
listening = False


def process_message(data, posted, cb):
  args = arguments(data)
  log('args', args)
  node = subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8')
  for channel in get_channels():
    if channel.id not in posted:
      posted[channel.id] = []
    if data["id"] in posted[channel.id]:
      log('message already received', channel.id)
      continue
    else:
      if data["newsType"] == "DISCORD_MESSAGE" and re.search(r"\b%s\b" % channel.id, data["body"].split(',')[1]): 
        log('Discarding message sent from this same channel', str(channel.id));
        continue
      if CHANNEL is None or CHANNEL == channel.id:
        log(channel.id, 'sending to channel: ' + str(node))
        cb(channel.id, node)
        posted[channel.id].append(data["id"])


def listen(cb):
  posted = {}
  url = 'https://cwtsite.com/api/message/listen'
  # url = 'http://localhost:9000/api/message/listen'
  while 1:
    log('', 'looping')
    messages = SSEClient(requests.get(url, stream=True))
    for msg in messages.events():
      if msg.event != "EVENT":
        continue
      data = json.loads(msg.data)
      log('EVENT', data)
      process_message(data, posted, cb)
    log('', 'out of loopery')


def get_channels():
  for guild in client.guilds:
    for channel in guild.text_channels:
      yield channel


def arguments(data):
  category = data["category"]
  username = data["author"]["username"]
  body = data["body"]
  newsType = data["newsType"]
  arr = ["node", SCRIPT + 'format.js', category, username, body, newsType]
  return list(filter(lambda x: x is not None, arr));


def send_message(channelId, message):
  client.loop.create_task(client.get_channel(channelId).send(message))


@client.event
async def on_ready():
  log('', 'ready')
  if LISTEN:
    t = threading.Thread(target=listen, args=(send_message,))
    t.start()
    log('listen thread started', 'continuing')
  else:
    log('not listening', 'listen by setting env LISTEN to 1')


@client.event
async def on_message(message):
  if message.author == client.user:
    return
  cmd = message.content.strip()
  log('on message', cmd)
  if cmd == '!cwt':
    await message.channel.send("Beep Bop CWT Bot. I act upon commands (see !cwtcommands) but I also mirror the CWT chat.")
    return
  link = 'https://discord.com/channels/' + str(message.channel.id)
  node = subprocess.run(
      ["node", SCRIPT + 'handle.js', 'DISCORD', link, message.author.display_name, cmd],
      stdout=subprocess.PIPE).stdout.decode('utf8')
  try:
    result = list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]
    log('responding', result)
    await message.channel.send(result)
  except:
    log(cmd, "did not yield a result")


def log(prefix, s):
  logger.info("APP - %s - %s" % (str(prefix), str(s)))


client.run(TOKEN)

