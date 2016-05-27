# Spotify-Ripper Vagrant

This tutorial describes how to install spotify-ripper as a virtual box with vagrant as provisioning tool. This tutorial is based on OSX El Capitan, you can also use this tutorial to install Spotify-Ripper on Windows or Linux.

## Description

"[..] Vagrant is computer software that creates and configures virtual development environments.[3] It can be seen as a higher-level wrapper around virtualization software such as VirtualBox, VMware, KVM and Linux Containers (LXC), and around configuration management software such as Ansible, Chef, Salt, and Puppet. [..]" [Link - Wikipedia](https://en.wikipedia.org/wiki/Vagrant_(software))

## Functionality

- Automatically installs spotify-ripper and all necessary packages
- Created a synced folder for Settings-, Spotify-Key-, and Output-Music-Files [Link - Synced Folders](https://www.vagrantup.com/docs/synced-folders/)
- Your Settings- and Spotify-Key files will be linked to the directory `.spotify-ripper`. So you are able to modify this files on your host.


## Tutorial

### Prerequisites

1. [Download](https://www.vagrantup.com/downloads.html) and install Vagrant
2. [Download](https://www.virtualbox.org/wiki/Downloads) and install VirtualBox
3. [Download](https://github.com/jrnewell/spotify-ripper/archive/master.zip) and unarchive Spotify-Ripper
4. Open your Terminal/Command Line Utility.

### Overview

The vagrant project directory contains a directory called `Shared`. This directory is shared with the VM and you are able to easily exchange files with it. Within this directory you have to place your required `spotify_appkey.key` and your optional `config.ini` file.

Due to the folder `Shared` it's recommended to use the parameter `directory = /vagrant/music`. You will find an example file of `config.ini`in the `default_config.ini`file. Copy this file to `config.ini` and extend it with your Spotify login credentials. If you paste the credentials in this file you only have to run `spotify <spotify:music_id>` at the command line (See later).

Before you run further, please check the following directory structure in `./Shared/`:

- [Folder] `Settings`
    - [File] `spotify_appkey.key` (Your spotify key)
    - [File] `config.ini` (Your configuration file)
    - [File] `default_config.ini` (Not required any more)
- [Folder] `Music` (Empty directory for music rips)

### Step-By-Step

Switch to your unarchived Spotify-Ripper directory, e.g. `cd spotify-ripper-master`

Now run vagrant command `vagrant up`. If you run Vagrant the first time, it will automatically download the lastest Ubuntu Trusty Tahr and install spotify-ripper with required packages. Lean back and wait. The first installation depends on your internet connection and takes 10 minutes at my MacBookPro.

After 10 minutes Vagrant created a virtual box :)

Run `vagrant ssh` to access the VM and run your spotify-ripper commands.

**!! Currently, there is a bug (Segmentation fault). Please run spotify-ripper as sudo !!**

### Furhter commands

- `Vagrant up`: Starts and initialize VM
- `Vagrant halt`: Stops the VM (Not destroying)
- `Vagrant destroy`: Stops and destroys the VM. You have to reinitialize the VM.
- `Vagrant ssh`: Access the VM

