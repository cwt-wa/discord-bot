#/bin/bash

url="https://discord.com/api/v8/applications/${APP_ID}/$1"
echo $url
cat $2

curl -iX POST "$url" \
  -H 'Authorization: Bot Nzc3MzA0MTU4NzUxNDI0NTYy.X7Be6Q.DoTJ68Hy8-kUBwykAlcS5_juSUw' \
  -H "Content-Type: application/json" \
  -d @$2

