import unittest
from unittest.mock import Mock
from beep import BeepBoop, Listener

class Env:
  
  def __init__(self, env):
    self.env = env

  def getenv(self, field):
    return self.env[field] if field in self.env else None

# todo append slash if it's not already there to SCRIPT env
#  and test this of course

class TestSum(unittest.TestCase):
  
  @classmethod
  def setUpClass(cls):
    cls.listener_mock = Mock()
    cls.listener_factory = lambda x: listener_mock()


  def test_init(self):
    client_mock = Mock()
    env = {"DISCORD_TOKEN": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, Env(env).getenv, self.listener_mock)
    client_mock.run.assert_called_once_with(env["DISCORD_TOKEN"])
    client_mock.listen.assert_not_called()
  

  def test_arguments_shoutbox(self):
    client_mock = Mock()
    env = {"SCRIPT": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, Env(env).getenv, self.listener_mock)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "Here is a message",
      "newsType": None
    }
    actual = beepBoop.arguments(message)
    self.assertEqual(
        actual,
        ["node", env["SCRIPT"] + "format.js", message["category"], 
          message["author"]["username"], message["body"]])
  

  def test_arguments_news(self):
    client_mock = Mock()
    env = {"SCRIPT": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, Env(env).getenv, self.listener_mock)
    message = {
      "category": "SHOUTBOX",
      "author": {"username": "Zemke"},
      "body": "BoolC,Taner,3,1",
      "newsType": "REPORT"
    }
    actual = beepBoop.arguments(message)
    self.assertEqual(
        actual,
        ["node", env["SCRIPT"] + "format.js", message["category"], 
          message["author"]["username"], message["body"], message["newsType"]])


  def test_listen_not(self):
    client_mock = Mock()
    env = {}
    thread_factory_mock = Mock()
    beepBoop = BeepBoop(
        client_mock,
        Env(env).getenv,
        self.listener_mock,
        thread_factory_mock)
    thread_factory_mock.inst.assert_not_called()


  def test_listen_not(self):
    client_mock = Mock()
    endpoint = "http://example.com"
    env = {"LISTEN": "1", "CHANNEL": "1234", "CWT_MESSAGE_SSE_ENDPOINT": endpoint}
    thread_factory_mock = Mock()
    listener_mock = Mock()
    listener_factory = lambda x: listener_mock(*x, endpoint, None, None)
    beepBoop = BeepBoop(
        client_mock,
        Env(env).getenv,
        listener_factory,
        thread_factory_mock)
    thread_factory_mock.inst.assert_called_once()
    listener_mock.assert_called_once_with(
          client_mock, int(env["CHANNEL"]), endpoint, None, None)


if __name__ == '__main__':
    unittest.main()

