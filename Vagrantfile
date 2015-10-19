Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.provision "shell", path: "RUNME.sh"
  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
  end
end

