FROM python:3.5

RUN git clone https://github.com/TeamHG-Memex/autologin.git /opt/autologin

# Set the default directory where CMD will execute
WORKDIR /opt/autologin

# Get pip to download and install requirements:
RUN pip install -r requirements.txt

RUN python setup.py build
RUN python setup.py install

# Expose ports
EXPOSE 8088
EXPOSE 8089

RUN apt-get update && apt-get install -y supervisor

COPY supervisord.conf supervisord.conf

# Set the default command to execute
# when creating a new container
CMD supervisord -c /opt/autologin/supervisord.conf
