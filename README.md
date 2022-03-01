# Tomate StatusNotifierItem Plugin

Show session progress on tray icon area.

## Installation

## Usage

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
