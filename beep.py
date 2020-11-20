# bot.py
from operator import itemgetter
import os
import re
import threading
import discord
from dotenv import load_dotenv
import json
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


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
    return threading.Thread(target=target, args=args)


class BeepBoop:

  say_beep_boop = \
      "Beep Bop CWT Bot. I act upon commands (see !cwtcommands)" \
      " but I also mirror the CWT chat."

  def __init__(self, client, getenv, listener_factory,
               thread_factory=ThreadFactory()):
    self.client = client
    self.env = Env(getenv)
    if self.env.listen:
      logger.info("I'm listening.")
      listener = listener_factory([self.client, self.env.channel])
      thread = thread_factory.inst(listener.listen, (-1, self.send_message))
      thread.start()
    else:
      logger.info('not listening, listen by setting env LISTEN to 1')
      if self.env.channel is not None:
        logger.info('CHANNEL env is set, but you\'re not listening')


  def send_message(channelId, message):
    self.client.loop.create_task(self.client.get_channel(channelId).send(message))


class Listener:

  def __init__(self, client, channel_to_mirror_to, node_runner, open_stream):
    self.posted = {}
    self.client = client
    self.node_runner = node_runner
    self.open_stream = open_stream
    self.channel_to_mirror_to = \
        int(channel_to_mirror_to) if channel_to_mirror_to is not None else None
    if self.channel_to_mirror_to is not None:
      logger.info('mirroring CWT chat to channel %s only.', self.channel_to_mirror_to)
    else:
      logger.info('mirroring CWT chat to all channels on server.')


  def listen(self, listen_iterations, cb):
    if listen_iterations == -1:
      while 1:
        self.loop(cb)
    else:
      for _ in range(listen_iterations):
        self.loop(cb)


  def loop(self, cb):
    logger.info('looping')
    messages = self.open_stream()
    for msg in messages.events():
      if msg.event != "EVENT":
        continue
      data = json.loads(msg.data)
      logger.info('EVENT %s', data)
      for channel in self.get_channels():
        self.process_message(data, channel.id, cb)
    logger.info('out of loopery')
    


  def process_message(self, data, channelId, cb):
    if channelId not in self.posted:
      self.posted[channelId] = []
    if data["id"] in self.posted[channelId]:
      logger.info('message already received %s', channelId)
    else:
      if data["newsType"] == "DISCORD_MESSAGE" and \
            re.search(r"\b%s\b" % channelId, data["body"].split(',')[1]): 
        logger.info('Discarding message sent from this same channel %s', str(channelId));
      elif self.channel_to_mirror_to is None or self.channel_to_mirror_to == channelId:
        formatted = self.node_runner.format(data)
        logger.info('sending to channel %s: %s', str(channelId), str(formatted))
        cb(channelId, formatted)
        self.posted[channelId].append(data["id"])


  def get_channels(self):
    for guild in self.client.guilds:
      for channel in guild.text_channels:
        yield channel


class NodeRunner:

  def __init__(self, script, runner):
    self.script = script if script.endswith("/") else script + "/"
    self.runner = runner
    import subprocess


  def handle(self, cmd, display_name, guildId, channelId):
    link = ('https://discord.com/channels/%s/%s' % (str(guildId), str(channelId)))
    arguments = ["node", self.script + 'handle.js', 'DISCORD', link, display_name, cmd]
    node = self.runner(arguments)
    return list(filter(lambda x: x.startswith("RES xx "), node.split('\n')))[0][7:]


  def format(self, data):
    category, author, body = itemgetter('category', 'author', 'body')(data)
    arguments = ["node", self.script + 'format.js', category, author["username"], body]
    if data["newsType"]:
      arguments.append(data["newsType"])
    return self.runner(arguments)


class EventHandler:

  other_user_dm_response = \
      "I don't offer private services, " \
      "but here are some commands you can give into the public channels I'm in:"

  confirm_all_channels = "Your message has been sent to all channels"

  def __init__(self, client, node_runner, channel_to_mirror_to):
    self.client = client
    self.node_runner = node_runner
    self.channel_to_mirror_to = channel_to_mirror_to

  async def on_message(self, message):
    if message.author == self.client.user:
      return
    cmd = message.content.strip()
    logger.info("message: %s", cmd)
    if message.channel is discord.DMChannel:
      await self.on_direct_message(message)
    elif cmd == '!cwt':
      logger.info("Received !cwt command")
      await message.channel.send(BeepBoop.say_beep_boop)
    elif cmd.startswith("!cwt"):
      logger.info("commands starts with !cwt")
      try:
        result = self.node_runner.handle(
            cmd, message.author.display_name,
            message.channel.guild.id,  message.channel.id)
        logger.info("sending node result: %s", result)
        await message.channel.send(result)
      except:
        logger.warning("error handling command %s", cmd)

  def register(self):
    @self.client.event
    async def on_ready():
      logger.info("ready")

    @self.client.event
    async def on_message(message):
      self.on_message(message)


  async def on_direct_message(self, message):
    if message.author != self.client.user:
      logger.info("dm from another user %s", message.content)
      await message.channel.send(EventHandler.other_user_dm_response)
      await message.channel.send(self.node_runner.command("!cwtcommands"))
    elif message.content.startswith("!adminannounce"):
      [command, channel, *content] = message.content.split(" ")
      content = " ".join(content)
      if channel == "-":  # to all channels
        logger.info('announcing to all channels')
        for c in self.client.get_all_channels():
          if isinstance(c, discord.TextChannel):
            await c.send(content)
        await message.channel.send(EventHandler.confirm_all_channels)
      elif channel == "x":
        if self.channel_to_mirror_to is None:
          logger.info("not announcing to env channel as it's not specified")
        else:
          logger.info('announcing to env channel of %s', self.channel_to_mirror_to)
          await self.client.get_channel(self.channel_to_mirror_to).send(content)
      else:  # to channel as given by command
        channel_to_send_to  = self.client.get_channel(int(channel))
        if channel_to_send_to is not None:
          logger.info('sending to channel %s as specified by the command', channel)
          await channel_to_send_to.send(content)
        else:
          logger.warning("Channel %s could not be sent to as it doesn't exist", channel)
    else:
      await message.channel.send(
          'Use "!cwtannounce - <message>" to send to all channels; '
          'or "!cwtannounce x <message>" to send to CHANNEL (from env); '
          'or "!cwtannounce <channelId> <message>" to send to specific channel.')


if __name__ == "__main__":
  load_dotenv()

  node_runner = NodeRunner(
      os.getenv("SCRIPT"),
      lambda args: subprocess.run(args, stdout=subprocess.PIPE).stdout.decode('utf8'))

  def listener_factory(args):
    import requests
    from sseclient import SSEClient
    logger.info("args given to listener_factory: %s", args)
    endpoint = os.getenv("CWT_MESSAGE_SSE_ENDPOINT")
    logger.info("Will be listening to %s", endpoint)
    return Listener(*args, node_runner, lambda: SSEClient(requests.get(endpoint, stream=True)))

  beepBoop = BeepBoop(
      client = discord.Client(),
      getenv = os.getenv,
      listener_factory = listener_factory)

  EventHandler(beepBoop.client, node_runner, beepBop.env.channel).register()

  beepBoop.client.run(self.env.token)


