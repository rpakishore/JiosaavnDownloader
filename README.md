<!--- Heading --->
<div align="center">
  <h1>Jiosaavn Downloader</h1>
  <p>
    Download Jiosaavn mp3 from unofficial API
  </p>
<h4>
    <a href="https://github.com/rpakishore/JiosaavnDownloader/">View Demo</a>
  <span> · </span>
    <a href="https://github.com/rpakishore/JiosaavnDownloader">Documentation</a>
  <span> · </span>
    <a href="https://github.com/rpakishore/JiosaavnDownloader/issues/">Report Bug</a>
  <span> · </span>
    <a href="https://github.com/rpakishore/JiosaavnDownloader/issues/">Request Feature</a>
  </h4>
</div>
<br />

![GitHub commit activity](https://img.shields.io/github/commit-activity/m/rpakishore/JiosaavnDownloader)
![GitHub last commit](https://img.shields.io/github/last-commit/rpakishore/JiosaavnDownloader)
<!-- Table of Contents -->
<h2>Table of Contents</h2>

- [1. About the Project](#1-about-the-project)
  - [1.1. Features](#11-features)
- [2. Getting Started](#2-getting-started)
  - [2.1. Prerequisites](#21-prerequisites)
  - [2.2. Installation](#22-installation)
- [3. Usage](#3-usage)
- [4. Roadmap](#4-roadmap)
- [5. License](#5-license)
- [6. Contact](#6-contact)
- [7. Acknowledgements](#7-acknowledgements)

<!-- About the Project -->
## 1. About the Project

<!-- Features -->
### 1.1. Features

- Currently uses free saavn.me api endpoints, additional endpoints can easily be added.
- Holds memory of previously downloaded files to prevent re-downloads.
- Can handle individual songs and playlists

<!-- Getting Started -->
## 2. Getting Started

<!-- Prerequisites -->
### 2.1. Prerequisites

python 3.11+

<!-- Installation -->
### 2.2. Installation

Clone repo and install with flit

```bash
  git clone https://github.com/rpakishore/JiosaavnDownloader.git
  cd JiosaavnDownloader
  pip install flit
  flit install --deps production
```

Alternatively, download the release and install with pip

```bash
  pip install jiosaavn-0.0.1-py2.py3-none-any.whl
```

<!-- Usage -->
## 3. Usage

Can be used as python package or through cli.

For cli, try

```bash
  jiosaavn --help
```

For python package

```python
#Initialize
from jiosaavn import JiosaavnDownload
from jiosaavn.API import SaavnMe

#Choose the database filepath & Final music location
saavn = JiosaavnDownload(cache_filepath='database.pkl', final_location='Y:\\Music')
#Choose downloader
saavn.set_downloader(downloader=SaavnMe())
#Download song, skip if previously downloaded
saavn.song(url='https://www.jiosaavn.com/album/sambar/MP5Da7jEhBQ_', skip_downloaded=True)
#Download all songs in playlists
playlists = [
    '109815423',        #Top Kuthu - Tamil
    '799619460',        #Tamil EDM,
    '1134651042',       #Tamil: India Superhits Top 50
    '80802063',         #Tamil Viral Hits
    '109118539',        #Motivational Hits - Tamil
    '83412571',         #Workout Beats - Tamil
    '837803163',        #Chill Hits - Tamil,
    '696005328',        #House Party - Tamil
    '67691546',         #Semma Mass - Tamil
    '1134705865',       #Malayalam: India Superhits Top 50
]
for playlist in playlists:
    saavn.playlist(id=playlist)
```

<!-- Roadmap -->
## 4. Roadmap

- [ ] Additional endpoints

<!-- License -->
## 5. License

See LICENSE.txt for more information.

<!-- Contact -->
## 6. Contact

Arun Kishore - [@rpakishore](mailto:pypi@rpakishore.co.in)

Project Link: [https://github.com/rpakishore/JiosaavnDownloader](https://github.com/rpakishore/JiosaavnDownloader)

<!-- Acknowledgments -->
## 7. Acknowledgements

Use this section to mention useful resources and libraries that you have used in your projects.

- [saavn.me](https://github.com/sumitkolhe/jiosaavn-api)