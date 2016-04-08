FROM python:2-onbuild

RUN git clone https://github.com/TeamHG-Memex/autologin.git /opt/autologin


# Set the default directory where CMD will execute
WORKDIR /opt/autologin
#ADD autologin/server.py /opt/autologin/autologin/server.py

# Get pip to download and install requirements:
RUN pip install -r requirements.txt

RUN python setup.py build
RUN python setup.py install

# Expose ports
EXPOSE 8088

# env in the ui/ directory
ENV PYTHONPATH=/opt/autlogin

# Set the default command to execute    
# when creating a new container
CMD python /opt/autologin/autologin/server.py

