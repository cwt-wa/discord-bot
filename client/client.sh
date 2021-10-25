#/bin/bash

url="https://discord.com/api/v8/applications/${APP_ID}/$1"
echo $url
cat $2

curl -iX POST "$url" \
  -H "Authorization: Bot $TOKEN" \
  -H "Content-Type: application/json" \
  -d @$2

