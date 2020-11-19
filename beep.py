# bot.py
from operator import itemgetter
import os
import re
import threading
import subprocess
import discord
from dotenv import load_dotenv
import json
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


def log(prefix, s):
  logger.info("APP - %s - %s" % (str(prefix), str(s)))


class Env:
  
  def __init__(self, getenv):
    self.token = getenv('DISCORD_TOKEN')
    self.script = getenv('SCRIPT') or './'
    self.listen = getenv('LISTEN') == "1"
    self.channel = int(getenv('CHANNEL')) if getenv('CHANNEL') is not None else None


class ThreadFactory:

  def __init__(self):
    import threading

  def inst(self, target, args):
    return threading.Thread(target=listener.listen, args=(self.send_message,))


class BeepBoop:

  def __init__(self, client, getenv, listener_factory,
               thread_factory=ThreadFactory()):
    self.client = client
    self.env = Env(getenv)
    self.client.run(self.env.token)
    if self.env.listen:
      log('APP', 'you wanted me to listen, I listen')
      listener = listener_factory([self.client, self.env.channel])
      thread = thread_factory.inst(listener.listen, (self.send_message,))
      thread.start()
    else:
      log('not listening', 'listen by setting env LISTEN to 1')
      if self.env.channel is not None:
        log('APP', 'CHANNEL env is set, but you\'re not listening')


  def arguments(self, data):
    category = data["category"]
    username = data["author"]["username"]
    body = data["body"]
    newsType = data["newsType"]
    arr = ["node", self.env.script + 'format.js', category, username, body, newsType]
    return list(filter(lambda x: x is not None, arr));


  def send_message(channelId, message):
    self.client.loop.create_task(self.client.get_channel(channelId).send(message))


class Listener:

  def __init__(self, client, channel_to_mirror_to, endpoint, requests, sseclient):
    self.requests, self.sseclient = itemgetter('requests', 'sseclient')(deps)
    log('APP', "in Listener, obtained deps")
    if channel_to_mirror_to is not None:
      log('APP', 'mirroring CWT chat to channel %s only.' % self.env.channel)
    else:
      log('APP', 'mirroring CWT chat to all channels on server.')


  def listen(self, cb):
    posted = {}
    while 1:
      log('', 'looping')
      messages = SSEClient(requests.get(self.url, stream=True))
      for msg in messages.events():
        if msg.event != "EVENT":
          continue
        data = json.loads(msg.data)
        log('EVENT', data)
        self.process_message(data, posted, cb)
      log('', 'out of loopery')


  def process_message(self, data, posted, cb):
    args = arguments(data)
    log('args', args)
    node = subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8')
    for channel in self.get_channels():
      if channel.id not in posted:
        posted[channel.id] = []
      if data["id"] in posted[channel.id]:
        log('message already received', channel.id)
        continue
      else:
        if data["newsType"] == "DISCORD_MESSAGE" and \
              re.search(r"\b%s\b" % channel.id, data["body"].split(',')[1]): 
          log('Discarding message sent from this same channel', str(channel.id));
          continue
        if self.channel_to_mirro_to is None or self.channel_to_mirro_to == channel.id:
          log(channel.id, 'sending to channel: ' + str(node))
          cb(channel.id, node)
          posted[channel.id].append(data["id"])


  def get_channels(self):
    for guild in self.client.guilds:
      for channel in guild.text_channels:
        yield channel


if __name__ == "__main__":
  load_dotenv()


  def listener_factory(*args):
    import requests
    from sseclient import SSEClient
    Listener(*args, os.getenv("CWT_MESSAGE_SSE_ENDPOINT"), requests, sseclient)


  beepBoop = BeepBoop(
      client = discord.Client(),
      getenv = os.getenv,
      listener_factory = listener_factory)


  @beepBop.client.event
  async def on_ready():
    log('', 'ready')


  @beepBop.client.event
  async def on_message(message):
    if message.author == client.user:
      return
    cmd = message.content.strip()
    log('on message', cmd)
    if cmd == '!cwt':
      await message.channel.send(
          "Beep Bop CWT Bot. I act upon commands (see !cwtcommands)"
          " but I also mirror the CWT chat.")
      return
    link = 'https://discord.com/channels/' + str(message.channel.id)
    node = subprocess.run(
        ["node", self.env.script + 'handle.js', 'DISCORD', link, message.author.display_name, cmd],
        stdout=subprocess.PIPE).stdout.decode('utf8')
    try:
      result = list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]
      log('responding', result)
      await message.channel.send(result)
    except:
      log(cmd, "did not yield a result")

