import unittest
from unittest.mock import Mock
from beep import BeepBoop

class Env:
  
  def __init__(self, env):
    self.env = env

  def getenv(self, field):
    return self.env[field] if field in self.env else None

# todo append slash if it's not already there to SCRIPT env
#  and test this of course

class TestSum(unittest.TestCase):
  
  def test_init(self):
    client_mock = Mock()
    client_mock.run = Mock(return_value="okay wow")
    env = {"DISCORD_TOKEN": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, 'localhost', Env(env).getenv)
    client_mock.run.assert_called_once_with(env["DISCORD_TOKEN"])
  

  def test_arguments_shoutbox(self):
    client_mock = Mock()
    env = {"SCRIPT": "fdasfdsa/"}
    beepBoop = BeepBoop(client_mock, 'localhost', Env(env).getenv)
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
    beepBoop = BeepBoop(client_mock, 'localhost', Env(env).getenv)
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


if __name__ == '__main__':
    unittest.main()

"""
env_mock = Mock()
env_mock.token = Mock(return_value="fdsafdasfdsa")
env_mock.script = Mock(return_value='./')
env_mock.listen = Mock(return_value=None)
env_mock.channel = Mock(return_value=None)
"""
