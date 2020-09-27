# Deployment Instructions

## Creating the Server
This application is hosted on [Amazon Lightsail](https://aws.amazon.com/lightsail/).
It's simple to create a server via the Lightsail interface. 

## SSH Keys
SSH keys can be needed for several different things. In order to create a key pair for
the server run the following command: 

```
ssh-keygen
```

Accepting the default values on the questions is probably fine. Once this completes
there will be two new files. 

```
~/.ssh/id_rsa      # Private Key
~/.ssh/id_rsa.pub  # Public Key
```

## Baseline Installs

```
sudo apt-get -y update
sudo apt-get -y install python3 python3-venv python3-dev
sudo apt-get -y install supervisor nginx git
```

## Installing the Application

```
git clone <repo_url>
cd <application_dir>
git checkout <version_tag>
```

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

```
pip install gunicorn
pip install pymysql   # If needed...

pip install -e .
```

```
echo "export FLASK_APP=chsmysteries.py" >> ~/.profile
```

## Gunicorn and Supervisor Setup

To start the application with Gunicorn, run: 

```
gunicorn -b localhost:8080 -w 4 <module_name>:<app_name>
```

#### Supervisor Config

The config file goes in `/etc/supervisor/conf.d/app.conf`.

```
cp deployment/supervisor.cfg /etc/supervisor/conf.d/chsmysteries.conf

sudo supervisorctl reload
```

## Nginx Setup

First, we need to remove the test site that's installed by default. 

```
sudo rm /etc/nginx/sites-enabled/default
```

The config file will go in `/etc/nginx/sites-enabled/charleston.ai`

```
sudo cp deployment/nginx.cfg /etc/nginx/sites-enabled/chsmysteries

sudo service nginx reload
```

## Database

Create a server with a database named `chsmysteries`

For the first time setup, you will need to run:

```
flask db upgrade
juniper data_pipeline
```


## Deploying Updates

```
(venv) $ git pull                              # download the new version
(venv) $ sudo supervisorctl stop <app_name>    # stop the current server
(venv) $ flask db upgrade                      # upgrade the database
(venv) $ sudo supervisorctl start <app_name>   # start a new server
```