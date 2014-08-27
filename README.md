commcarehq-venv
===============

A premade virtualenv for commcarehq - to aid in travis building and possible dev deployments.

This venv was built on a ubuntu 12.04 64 bit machine running python 2.7.3.


Bootstrapping the Virtualbox (First time only)
----------------------------

The first time you want to update this virtualenv, you'll have to set up a vagrant box that matches
the exact setup. Important to note, you do _not_ need an Ubuntu box yourself, and even if you do, it's better to use vagrant so we have more control making the environment uniform for everyone.

To do this first install [Vagrant](http://docs.vagrantup.com/v2/installation/). (This requires VirtualBox >= 4.2.16.)

The way Vagrant works is that you give your vagrant box a home on your machine, say `/path/to/hq_env-vagrant`. Then anything you put under that directory will be available once you log into that box under `/vagrant/`. We're going to add commcarehq-env and commcare-hq under `/path/to/hq_env-vagrant`, so that they show up in the box under `/vagrant/commcarehq-env` and `/vagrant/commcare-hq` respectively.

Host Machine:
The first step is to create the path to hq_env-vagrant on the host machine.
```mkdir -p /path/to/hq_env-vagrant```

We can now add the prebuilt box referenced at http://www.vagrantbox.es/ with the following command,
initialize the directory, boot up the machine, and ssh into it with:

```bash
cd /path/to/hq_env-vagrant
vagrant box add ubuntu-12.04-64 http://cloud-images.ubuntu.com/vagrant/precise/current/precise-server-cloudimg-amd64-vagrant-disk1.box
vagrant init ubuntu-12.04-64
vagrant up
vagrant ssh
```

Vagrant Guest:
Now that we're in the vagrant guest, we need to switch to the shared directory, install git, clone the github repos and initiate the submodule downloads.
```bash
cd /vagrant
sudo apt-get install git
git clone git@github.com:dimagi/commcarehq-venv.git
git clone git@github.com:dimagi/commcare-hq.git
cd commcare-hq
git submodule update --init
cd ..
```

Our travis build expects a virtualenv at `/home/travis` so we'll need to symlink it to that location for all the refs to work out.

```bash
vagrant@precise64 $ sudo mkdir -p /home/travis
vagrant@precise64 $ sudo chown vagrant:vagrant /home/travis
vagrant@precise64 $ ln -s /vagrant/commcarehq-venv/hq_env /home/travis/virtualenv
```

You can log out of your vagrant box with ^D or logout as you would any ssh session. To shut down your vagrant box while preserving its state run `vagrant halt`; to wipe it so you can start from scratch run `vagrant destroy`.

Building the virtualenv
-----------------------

Run these steps to set up your environment.
Note: Windows requires that these commands run as administrator to allow NPM to create symlinks. In Windows, right click your bash or command program and left click "Run as administrator..." before executing the following commands.

Host Machine:
```bash
cd /path/to/hq_env-vagrant
vagrant up
vagrant ssh
```

Vagrant Guest:
```bash
vagrant@precise64 $ source /home/travis/virtualenv/bin/activate
vagrant@precise64 $ cd /vagrant/commcare-hq
```

Then you should probably rerun this everytime, but you definitely need it the first time

```bash
vagrant@precise64 $ bash -ex install.sh
```

The following commands will actually update the virtualenv

```bash
vagrant@precise64 $ bash scripts/uninstall-requirements.sh
vagrant@precise64 $ pip install -r requirements/requirements.txt -r requirements/dev-requirements.txt
vagrant@precise64 $ pip install coveralls coverage unittest2 mock
```
