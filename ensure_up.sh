#!/bin/bash

ps -ef | grep 'manage.py \+solve' > /dev/null

if [[ "$?" != "0" ]] ; then
  nohup /home/mgeorg/production_scheduler/manage.py solve &
fi
