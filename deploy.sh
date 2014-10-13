#!/bin/bash

sudo ./manage.py collectstatic
sudo cp solver/templates/solver/instructions.html /var/www
sudo /etc/init.d/apache2 restart
