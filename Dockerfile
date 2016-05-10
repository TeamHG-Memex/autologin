FROM python:3.5

RUN apt-get update && apt-get install -y supervisor tree

ADD . /opt/autologin

# Set the default directory where CMD will execute
WORKDIR /opt/autologin
RUN tree

# Get pip to download and install requirements:
RUN pip install -r requirements.txt
RUN python setup.py install

# Expose ports
EXPOSE 8088 8089

# Set the default command to execute
# when creating a new container
CMD supervisord -c /opt/autologin/supervisord.conf
