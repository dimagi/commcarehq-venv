# A quick vagrant config to fire up a debian box and build the package
Vagrant.configure("2") do |config|
  config.vm.box = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"
  config.vm.synced_folder "hq_env", "/home/travis/virtualenv"

  config.vm.provider :virtualbox do |vb|

    # DNS => NAT
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]

    # Enable symlinks, which VirtualBox disables for "security" reasons (https://www.virtualbox.org/ticket/10085#comment:12)
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate/build", "1"]
  end

end
