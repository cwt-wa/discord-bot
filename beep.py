# bot.py
from operator import itemgetter
import os
import re
import threading
import discord
from dotenv import load_dotenv
import json
import logging
import subprocess
from subprocess import CalledProcessError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
zemke_id = 507097491762839555


class NodeRunnerError(Exception):
  pass


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


  def send_message(self, channelId, message):
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
    if "id" not in data:
      logger.warning("Data has no ID: %s", data)
      return;
    if data["id"] in self.posted[channelId]:
      logger.info('message already received %s', channelId)
    else:
      if "newsType" in data and data["newsType"] == "DISCORD_MESSAGE" and \
            re.search(r"\b%s\b" % channelId, data["body"].split(',')[1]): 
        logger.info('Discarding message sent from this same channel %s', str(channelId));
      elif self.channel_to_mirror_to is None or self.channel_to_mirror_to == channelId:
        try:
          formatted = self.node_runner.format(data)
          logger.info('sending to channel %s: %s', str(channelId), str(formatted))
          cb(channelId, formatted)
        except CalledProcessError as err:
          logging.exception("Couldn't format, not sending.")
        except:
          logging.exception("Error while sending")
        self.posted[channelId].append(data["id"])


  def get_channels(self):
    for guild in self.client.guilds:
      for channel in guild.text_channels:
        yield channel


class NodeRunner:

  def __init__(self, script, runner):
    self.script = script if script.endswith("/") else script + "/"
    self.runner = runner


  def handle(self, cmd, display_name, guild_id, channel_id):
    link = ('https://discord.com/channels/%s/%s' % (str(guild_id), str(channel_id)))
    arguments = ["node", self.script + 'handle.js', 'DISCORD', link, display_name, cmd]
    return self._run(arguments)


  def format(self, data):
    category, author, body = itemgetter('category', 'author', 'body')(data)
    arguments = ["node", self.script + 'format.js', category, author["username"], body]
    if "newsType" in data and data["newsType"]:
      arguments.append(data["newsType"])
    return self._run(arguments)


  def _run(self, args):
    node = self.runner(args)
    node.check_returncode()
    stdout = node.stdout.decode('utf8')
    ll = list(filter(lambda x: x.startswith("RES xx "), stdout.split('\n')))
    try:
      return ll[0][7:]
    except:
      logger.info("stdout: %s", stdout)
      raise NodeRunnerError()


class EventHandler:

  other_user_dm_response = \
      "I don't offer private services, " \
      "but here are some commands you can give into the public channels I'm in:"

  confirm_all_channels = "Your message has been sent to all channels"

  not_specified = "Not announcing to env channel as it's not specified."

  confirm_specific_channel = "Message has been sent to that specific channel."

  def __init__(self, client, node_runner, channel_to_mirror_to):
    self.client = client
    self.node_runner = node_runner
    self.channel_to_mirror_to = channel_to_mirror_to

  async def on_message(self, message):
    if message.author == self.client.user:
      return
    cmd = message.content.strip()
    logger.info("%s: %s", message.author.display_name, cmd)
    if isinstance(message.channel, discord.DMChannel):
      logger.info("is direct message")
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
        logger.exception("error handling command")

  def register(self):
    @self.client.event
    async def on_ready():
      logger.info("ready")

    @self.client.event
    async def on_message(message):
      await self.on_message(message)


  async def on_direct_message(self, message):
    if message.author.id != zemke_id:
      logger.info("dm from another user %s", message.content)
      await message.channel.send(EventHandler.other_user_dm_response)
      #  DMChannel doesn't have guild
      try:
        await message.channel.send(self.node_runner.handle(
            "!cwtcommands", message.author.display_name, "", message.channel.id))
      except:
        logger.exception("Failed responding to DM from other user")
        await message.channel.send("Sorry, something went wrong.")
    elif message.content.startswith("!adminannounce"):
      [command, channel, *content] = message.content.split(" ")
      content = " ".join(content).strip()
      if channel == "-":  # to all channels
        logger.info('announcing to all channels')
        for c in self.client.get_all_channels():
          if isinstance(c, discord.TextChannel):
            await c.send(content)
        await message.channel.send(EventHandler.confirm_all_channels)
      elif channel == "x":  # to channel from env
        if self.channel_to_mirror_to is None:
          logger.info(EventHandler.not_specified)
          await message.channel.send(EventHandler.not_specified)
        else:
          logger.info('announcing to env channel of %s', self.channel_to_mirror_to)
          await self.client.get_channel(self.channel_to_mirror_to).send(content)
          await message.channel.send("Message has been sent.")
      else:  # to channel as given by command
        channel_to_send_to  = self.client.get_channel(int(channel))
        if channel_to_send_to is not None:
          logger.info('sending to channel %s as specified by the command', channel)
          await channel_to_send_to.send(content)
          await message.channel.send(EventHandler.confirm_specific_channel)
        else:
          logger.warning("Channel %s could not be sent to as it doesn't exist", channel)
    else:
      await message.channel.send(
          'Use "!adminannounce - <message>" to send to all channels; '
          'or "!adminannounce x <message>" to send to CHANNEL (from env); '
          'or "!adminannounce <channelId> <message>" to send to specific channel.')


if __name__ == "__main__":
  load_dotenv()

  node_runner = NodeRunner(
      os.getenv("SCRIPT"),
      lambda args: subprocess.run(args, stdout=subprocess.PIPE))

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

  EventHandler(beepBoop.client, node_runner, beepBoop.env.channel).register()

  beepBoop.client.run(beepBoop.env.token)


