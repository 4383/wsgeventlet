# wsgeventlet

Debug mod_msgi/uswgi and AMQP heartbeat with and without eventlet environment

This is a minimal POC to test AMQP use cases with process who run under
a defined context:
- using mod_wsgi or uwsgi
- with or without the stdlib monkey patched with eventlet

This piece of the POC doesn't care about application server (mod_wsgi/uwsgi),
this piece is only focused on the eventlet purpose (activate/deactivate).

For further informations about the application server please report to the root
path of this project (root README file)

## Prerequisite

- a python 3 environment
- PBR is needed
- a setup and running RabbitMQ server is needed

## Install

For a standalone usage free from environment context please use:

```shell
$ git clone https://github.com/4383/wsgeventlet
$ cd wsgeventlet/payload
$ python -m pip install pbr
$ python setup.py install
```

## Usage

Note: by default we will run a monkey patched environment.

To simply run the AMQP heartbeat (default monkey patched) use the following comand:

```shell
$ wsgeventlet
```

To run AMQP heartbeat in a non eventlet monkey patched environment use the command bellow:

```shell
$ wsgeventlet --eventlet-turned-off
```
