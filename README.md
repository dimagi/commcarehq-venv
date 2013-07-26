commcarehq-venv
===============

A premade virtualenv for commcarehq - to aid in travis building and possible dev deployments.

This venv was built on a ubuntu 12.04 64 bit machine running python 2.7.3

Updating the virtualenv
-----------------------

You do _not_ need an Ubuntu box yourself, if you have [Vagrant](http://docs.vagrantup.com/v2/installation/) installed. 
(This requires VirtualBox >= 4.2.16)

```
$ vagrant up
```

You will need to run a few things manually, until we provision the box more thoroughly and/or have a Makefile.
It isn't that hard or common so meh.

The starting commands

```
$ vagrant ssh
vagrant@precise64 $ sudo apt-get update
vagrant@precise64 $ sudo apt-get install python-pip
vagrant@precise64 $ sudo pip install virtualenv
vagrant@precise64 $ virtualenv --no-site-packages --distribute /home/travis/virtualenv
^D
```

And then you will not need to do that again, but can update the virtualenv like so. The 
`pip install` requires the submodules to be present, so you may as well share the entire
commcare-hq git clone with the virtualenv. You can edit the Vagrantfile or just copy
the thing.

Some pip requirements have apt-get requirements than install.sh should manage.

```
$ cp -r /path/to/commcare-hq ./commcare-hq
$ vagrant ssh
vagrant@precise64 $ source /home/travis/virtualenv/bin/activate
vagrant@precise64 $ cd /vagrant/commcare-hq
vagrant@precise64 $ bash -ex install.sh
vagrant@precise64 $ pip install -r requirements/requirements.txt -r requirements/dev-requirements.txt
vagrant@precise64 $ pip install coveralls coverage unittest2 mock # These are separately install by travis because some of our deps are not so well expressed
^D
```
