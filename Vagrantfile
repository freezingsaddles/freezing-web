# -*- mode: ruby -*-
# vi: set ft=ruby :

# This vagrantfile is currently just setup to create a MySQL server.  Eventually it will be expanded to
# setup a full working stack.

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # config.vm.network "forwarded_port", guest: 80, host: 8080

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  config.vm.box = "ubuntu/trusty64"
  
  #config.vm.network "private_network", type: "dhcp"
  config.vm.network "forwarded_port", guest: 3306, host: 3306

$script = <<SCRIPT
# Make sure we're up-to-date.
apt-get update

# Install Python Development packages
apt-get install -y python-dev python-pip python-paver python-virtualenv

# Install depenency packages
apt-get install -y mysql-server

# Install Git
apt-get install -y git

cd /opt/
git clone https://github.com/hozn/bafs.git

SCRIPT

  config.vm.provision "shell", inline: $script

  config.vm.hostname = "freezingdb.localhost"

end