cmmcarehq-venv
===============

A premade virtualenv for [commcarehq](https://github.com/dimagi/commcare-hq) - to aid in travis building and dev deployments.

This venv was built on a ubuntu 12.04 64 bit machine running python 2.7.3.

This readme describes how to setup and update the virtualenv using vagrant and VirtualBox.

# First time setup

## Bootstrapping the Virtualbox

The first time you want to update this virtualenv, you'll have to set up a vagrant box that matches
the exact setup. Important to note, you do _not_ need an Ubuntu box yourself, and even if you do, it's better to use vagrant so we have more control making the environment uniform for everyone.

To do this first install [Vagrant](http://docs.vagrantup.com/v2/installation/). (This requires VirtualBox >= 4.2.16.)

The way Vagrant works is that you give your vagrant box a home on your machine, say `/path/to/hq_env-vagrant`. Then anything you put under that directory will be available once you log into that box under `/vagrant/`. We're going to add commcarehq-env and commcare-hq under `/path/to/hq_env-vagrant`, so that they show up in the box under `/vagrant/commcarehq-env` and `/vagrant/commcare-hq` respectively.

## Setup the vagrant machine

The first step is to create the path to hq_env-vagrant on the host machine.
```mkdir -p /path/to/hq_env-vagrant```

We can now add the prebuilt box referenced at http://www.vagrantbox.es/ with the following command,
initialize the directory, boot up the machine, and ssh into it with:

```bash
cd /path/to/hq_env-vagrant
vagrant box add ubuntu-12.04-64 http://cloud-images.ubuntu.com/vagrant/precise/current/precise-server-cloudimg-amd64-vagrant-disk1.box
vagrant init ubuntu-12.04-64
vagrant up
```

## Setup the repositories

You can either setup the repositories from the host or the guest.

Both of these will require copying files from the host to the guest. See the vagrant tips section below for more information.

### Option 1: On the host

This is the easiest way to setup the repositories. Go into the shared directory (where the `Vagrantfile` is) and just clone them as usual. Then reload vagrant to set the permissions correctly.

```bash
git clone git@github.com:dimagi/commcarehq-venv.git
git clone git@github.com:dimagi/commcare-hq.git
cd commcare-hq
git submodule update --init --recursive
vagrant reload
```

### Option 2: On the guest

First login to the guest machine:

```bash
vagrant ssh
```

Then copy your ssh keys onto the guest machine and put them in the right spot for git to access them. (Note: this needs docs)

After that, on the guest machine, switch to the shared directory, install git, clone the github repos and initiate the submodule downloads.
```bash
cd /vagrant
git clone git@github.com:dimagi/commcarehq-venv.git
git clone git@github.com:dimagi/commcare-hq.git
cd commcare-hq
git submodule update --init --recursive
cd ..
```

## Setup travis directories

Our travis build expects a virtualenv at `/home/travis` so we'll need to symlink it to that location for all the refs to work out.

If you're not already on the guest OS, login now using `vagrant ssh`. Then run the following:

```bash
vagrant@precise64 $ sudo mkdir -p /home/travis
vagrant@precise64 $ sudo chown vagrant:vagrant /home/travis
vagrant@precise64 $ ln -s /vagrant/commcarehq-venv/hq_env /home/travis/virtualenv
```

## Install pip dependencies

On the guest run the following to install pip dependencies:

```bash
sudo apt-get install git  # not necessary if already installed when initializing the repositories
sudo apt-get install python-dev
```

## (Optional) Install HQ dependencies

This is not necessary, but if you want to run HQ on the guest OS then you should also install the dependencies (e.g. couchdb, postgres, etc.). This can be done using the `install.sh` scipt.

Note: Windows requires that these commands run as administrator to allow NPM to create symlinks. In Windows, right click your bash or command program and left click "Run as administrator..." before executing the following commands.


```bash
vagrant@precise64 $ bash -ex install.sh
```

# Updating the virtualenv (steady-state workflow)


## Log in to the guest

If you're not already logged into the guest, make sure that it is up and running and login by running the following on the host machine:

```bash
cd /path/to/hq_env-vagrant
vagrant up
vagrant ssh
```

## Enter the virtualenv

On the guest run the following:

```bash
vagrant@precise64 $ source /home/travis/virtualenv/bin/activate
vagrant@precise64 $ cd /vagrant/commcare-hq
```

## Update the virtualenv

The following commands will actually update the virtualenv

```bash
vagrant@precise64 $ bash scripts/uninstall-requirements.sh
vagrant@precise64 $ pip install -r requirements/requirements.txt -r requirements/dev-requirements.txt
vagrant@precise64 $ pip install coveralls coverage unittest2 mock
```

## Commit changes

Finally, verify everything looks good, and commit and push the changes!

Wherever you're git repo is run the following:

```bash
git checkout -b update-env
git add -A
git commit -m "updating the virtualenv"
git push origin update-env
```

# Vagrant tips

## Copying files

Additional information on copying files and shared directories can be found [in the vagrant docs](http://docs.vagrantup.com/v2/synced-folders/basic_usage.html) or [on stack overflow](http://stackoverflow.com/questions/16704059/easiest-way-to-copy-a-single-file-from-host-to-vagrant-guest).

## Logging out

You can log out of your vagrant box with ^D or logout as you would any ssh session.

## Managing the guest box

To shut down your vagrant box while preserving its state run `vagrant halt`.

To wipe it so you can start from scratch run `vagrant destroy`.
