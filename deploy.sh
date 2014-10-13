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

sudo chown mgeorg:www-data -R .
sudo chown mgeorg:www-data /tmp/django*.log
sudo chmod 660 /tmp/django*.log
sudo sed -i -r 's/^\s*PRODUCTION\s*=\s*FALSE\s*;?\s*$/PRODUCTION = TRUE/' scheduler/settings.py
sudo ./manage.py collectstatic
sudo vi /etc/apache2/sites-enabled/000-default.conf
sudo /etc/init.d/apache2 restart
