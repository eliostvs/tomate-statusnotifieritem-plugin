# Tomate StatusNotifierItem Plugin

Show session progress on tray icon area.

## Installation

### Ubuntu 20.04+

If you have installed the program using the **old ppa repository** uninstall the old version first.
If you use an Ubuntu-based distro, such as Mint, manually set the **RELEASE** variable to the Ubuntu version number, such as 16.04, rather than running the sed script bellow.

    RELEASE=`sed -n 's/VERSION_ID="\(.*\)"/\1/p' /etc/os-release`
    sudo wget -O- http://download.opensuse.org/repositories/home:/eliostvs:/tomate/xUbuntu_$RELEASE/Release.key | sudo apt-key add -
    sudo bash -c "echo 'deb http://download.opensuse.org/repositories/home:/eliostvs:/tomate/xUbuntu_$RELEASE/ ./' > /etc/apt/sources.list.d/tomate.list"
    sudo apt-get update && sudo apt-get install tomate-statusnotifieritem-plugin

### Debian 10+

    RELEASE=`sed -n 's/VERSION_ID="\(.*\)"/\1\.0/p' /etc/os-release`
    sudo wget -O- http://download.opensuse.org/repositories/home:/eliostvs:/tomate/Debian_$RELEASE/Release.key | sudo apt-key add -
    sudo bash -c "echo 'deb http://download.opensuse.org/repositories/home:/eliostvs:/tomate/Debian_$RELEASE/ ./' > /etc/apt/sources.list.d/tomate.list"
    sudo apt-get update && sudo apt-get install tomate-statusnotifieritem-plugin

### Opensuse Tumbleweed

    sudo zypper ar -f http://download.opensuse.org/repositories/home:/eliostvs:/tomate/openSUSE_Tumbleweed/home:eliostvs:tomate.repo
    sudo zypper install tomate-statusnotifieritem-plugin

### Fedora 32+

    RELEASE=`cat /etc/fedora-release | grep -o '[0-9][0-9]*'`
    sudo dnf config-manager --add-repo http://download.opensuse.org/repositories/home:/eliostvs:/tomate/Fedora_$RELEASE/home:eliostvs:tomate.repo
    sudo dnf install tomate-statusnotifieritem-plugin

### Arch

The packages are available in [aur repository](https://aur.archlinux.org/packages/tomate-gtk/)

## Development

Install the following native dependencies in you system:

- Python3
- pip
- make 
- git 
- git-flow
- tomate/tomate-gtk

Install the Python development dependencies:

```bash
pip install --user black bumpversion copier pytest pytest-cov pytest-flake8 pytest-mock pre-commit
```

Create the plugin project:

```bash
copier gh:eliostvs/tomate-plugin-template path/to/plugin/project`
```

### Media Files

If this plugin uses media files (icons, mp3, etc), copy them to the **data** directory in root of the repository.

### Testing

Personalize the .pre-commit-config.yaml

Format the files using [black](https://pypi.org/project/black/):

```bash
make format
```

Run test in your local environment:

```bash
make test
```

Run test inside the docker:

```bash
make docker-test
```

Test manually the plugin:

```bash
ln -s ~/.local/share/tomate/plugins path/to/plugin/project/data/plugins
tomate-gtk -v
```

Then activate the plugin through the settings.

### Release

Update the *[Unrelease]* section in the CHANGELOG.md file then:

`make release-[patch|minor|major]`
