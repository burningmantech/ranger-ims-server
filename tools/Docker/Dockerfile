FROM python:3.6.2-alpine

COPY . /docker_install

RUN /docker_install/install

EXPOSE 8080

CMD [ "ims_server", "--config", "/opt/ims/conf/imsd.conf", "--log-file", "-" ]
