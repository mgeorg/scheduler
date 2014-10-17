#!/bin/bash

DELETE_DATABASE=$1
shift
if [[ "$DELETE_DATABASE" = "--delete" ]]; then
  echo "Deleting database"
  sudo rm solver/migrations/0*.py
  sudo rm db.sqlite3
  sudo ./manage.py makemigrations
  sudo ./manage.py migrate
  sudo chown mgeorg:www-data db.sqlite3
  sudo chmod 660 db.sqlite3
fi

if [[ "$DELETE_DATABASE" = "--production" ]]; then
  echo "Deploying to production"
else
  PRODUCTION=$1
  shift
fi
if [[ "$PRODUCTION" = "--production" ]]; then
  sudo sed -i -r 's/^\s*PRODUCTION\s*=\s*False\s*;?\s*$/PRODUCTION = True/i' scheduler/settings.py
  sudo ./manage.py collectstatic
  sudo vi /etc/apache2/sites-enabled/000-default.conf
  sudo /etc/init.d/apache2 restart
  sudo chown mgeorg:www-data -R .
  sudo chown mgeorg:www-data /tmp/django*.log
  sudo chmod 660 /tmp/django*.log
fi

