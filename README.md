# Reclaim TikTok

## Disclaimer
This code is developed by our Team Reclaim TikTok for the AI for Impact Hackathon. The code, including any associated documentation, data etc., is the intellectual property of our Team.
## Usage Restrictions
This code shall not be used, copied, modified, or distributed without the explicit written consent of us. Any use of this code without permission is prohibited.



## Setup 

### Conda installation
Run:

```conda env create -f environment.yml```

### Install Repo
Install our reklaim-tiktok package to ensure imports are working.

`pip install -e .`

### Unofficial TikTok API
To work with the [Unofficial TikTok API](https://github.com/davidteather/TikTok-Api):

```python -m playwright install```

### Azure SQL Database
We need to ensure that we have [ODBC installed](https://learn.microsoft.com/en-us/sql/connect/odbc/microsoft-odbc-driver-for-sql-server?view=sql-server-ver16).

SEE:

[Windows](https://learn.microsoft.com/en-us/sql/connect/odbc/windows/microsoft-odbc-driver-for-sql-server-on-windows?view=sql-server-ver16)

[Linux](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver16&tabs=alpine18-install%2Calpine17-install%2Cdebian8-install%2Credhat7-13-install%2Crhel7-offline)

[macOS](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos?view=sql-server-ver16)


### Pre-commit hook 
To maintain a clean and standardized environment and codebase please use pre-commit hooks (see the Development section for more details). To use pre-commit hooks we need to run:

`pre-commit install`

### FFMPEG
For using the speech to text module (2):
Make sure you have ffmeg installed and the `IMAGEIO_FFMPEG_EXE` enironment variable is set to the installation path (`which ffmpeg`).

## Usage

Make sure to create a .env file in the working directory with all defined environment variables. See Notion for details.

## Development

### Styling and formatting
```sh
black . # In place formatter, adheres mostly to PEP8
flake8  # Code linter with stylistic conventions adhering to PEP8
isort . # Sorts and formats imports in python files
```

### Make commands
You can use `make` to execute targets defined in the `Makefile`. If make is not installed, run `sudo apt install make`.
```sh
# See available make commands
make help
# Execute several clean commands
make clean
# Execute style formatting
make style
# Execute all pre-commit hooks
make pre-commit
```

### Configs
The development tools are configured in the following files. While trying to adhere to standards, we made some exceptions and ignored some directories.
```sh
.flake8 # flake8
pyproject.toml # black, isort, pytest
Makefile # make
.pre-commit-config
```
</details>

### IDE settings (VScode, Pycharm)
You can also change settings in your IDE to do auto formatting (black) on save and run flake8 on save if you do not want to run them via terminal. Here are articles to setup [black on Pycharm](https://akshay-jain.medium.com/pycharm-black-with-formatting-on-auto-save-4797972cf5de), [black on VScode](https://dev.to/adamlombard/how-to-use-the-black-python-code-formatter-in-vscode-3lo0), [flake8 on VScode](https://code.visualstudio.com/docs/python/linting).


