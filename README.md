# ClientParser

![License](https://img.shields.io/badge/license-MIT-orange.svg)

This repository contains the necessary files and documentation for parsing DNS and DHCP and saving the results to MariaDB.


## Table of Contents
- [Requirements](#requirements)
- [Contributing](#contributing)
- [Usage](#usage)
- [License](#license)


## Requirements
> [Windows 10/11 or Windows Server 2019/2022](https://www.microsoft.com/en-us/windows/)   
[RSAT: DHCP and DNS Tools](https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/remote-server-administration-tools)  
[MariaDB version 10.5.22 or higher](https://mariadb.org/)  
[Python 3.12 or higher](https://www.python.org/)

#### Python packages
- python >= 3.12
- python-dotenv >= 1.0.1
- sqlalchemy >= 2.0.38 


## Usage
This project is able to read DHCP and DNS data, parse the results and save everything into MariaDB database tables;

Before you begin, ensure you meet the [requirements](#requirements) for this project.

To use it first you must clone the repository:
```bash
git clone https://github.com/CARS-IT/ClientParser.git && cd ClientParser
```

Rename **.env-example** to **.env** and modify it to fit your needs. Once this is complete you can populate the database
by running:
```bash
python ClientParser.py
```


## Contributing
All contributions to the CARS-IT ClientParser project are welcome! Here are some ways you can help:
- Report a bug by opening an [issue](https://github.com/CARS-IT/ClientParser/issues).
- Add new features, fix bugs or improve documentation by submitting a [pull request](https://github.com/CARS-IT/ClientParser/pulls).

Please adhere to the [GitHub flow](https://docs.github.com/en/get-started/quickstart/github-flow) model when making your contributions! This means creating a new branch for each feature or bug fix, and submitting your changes as a pull request against the main branch. If you're not sure how to contribute, please open an issue and we'll be happy to help you out.

By contributing to the CARS-IT ClientParser project, you agree that your contributions will be licensed under the MIT License.

[back to top](#table-of-contents)


## License
CARS-IT ClientParser is distributed under the MIT license. You should have received a [copy](LICENSE) of the MIT License along with this program. If not, see https://mit-license.org/ for additional details.