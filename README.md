# Smackademia: Computational Linguistics

An interactive e-book for learning how to intergrate code into linguistic research.

# Setup:
## 1. Install the tool‑chain and clone the project
You need Git to pull the code and push changes back to GitHub.
For Windows, you may need to follow the instructions from here: [https://git-scm.com/downloads/win](https://git-scm.com/downloads/win).

```bash
# Linux (Ubuntu/Debian)
sudo apt update && sudo apt install git

# Windows (PowerShell ≥ 5)
winget install --id Git.Git -e
```
### 1.2 Quarto CLI
Quarto performs the actual rendering. Make sure you install v1.5 or later.
Windows users can follow the instructions from the offical Quarto Website to install R and Quarto: [https://quarto.org/docs/get-started/](https://quarto.org/docs/get-started/).

```bash
# Linux
sudo apt install r-base

# Windows
winget install --id RProject.R -e

```
### 1.3 R & required packages
Afterwards, inside R,  you can install the requried runtimes:

```r
install.packages(c("knitr", "jsonlite", "htmlwidgets"))
```

### 1.4 Node.js 
If you plan to edit the files locally and view the changes, you will need Node (>18) to run quarto-live.

```bash
# Linux
sudo apt install nodejs npm        # or use nvm if you prefer

# Windows
winget install OpenJS.NodeJS.LTS
```
### 1.5 Clone the repository
```bash
git clone https://github.com/michaelbennieUFL/Smackademia-Computational-Linguistics.git
cd Smackademia-Computational-Linguistics
# generates live-runtime.js, pyodide-worker.js, etc.
cd live-runtime
npm ci
npm run build        
cd ..
```
## Render and test the site locally

When you’re ready to see the project in action, you don’t need to push anything online first. Quarto includes its own lightweight development server. From the repository root, simply run **make preview** while in the **docs** file directory. If you're system has make installed, you can just run **make preview**.The docs site opens at [http://localhost:4200 by default.](http://localhost:4200) by default.

As you click around, be sure to run a few interactive cells marked ```{webr}``` or ```{pyodide}```. Because the underlying R and Python engines are compiled to WebAssembly and shipped with the page, your browser should execute the code instantly without any server round-trip; if a cell fails to run, that’s a sign you’re missing a dependency or your browser is blocking WebAssembly.


If you want to add more chapters, you can go to the ```docs/_quarto.yml``` page and change the contents under chapters. Each chapter links to a file under a specific directory.
Here is some example code for how to setup a page:

```r
---
title: A Curious Quirk of Word Frequency
subtitle: How word distributions follow a general trend.
format: live-html
engine: knitr
toc: true
resources:
  - data
webr:
  resources:
    - data
pyodide:
  resources:
    - data
---
{{< include ../_extensions/live/_knitr.qmd >}}


Have you ever paused to ponder which words are the most common ones in the vast landscape of the English language?

```

## 3. Publish website:
For repeatability, this project uses continuous deployment so every push to main republishes automatically.To publish the website, you can simply push to the main branch and it will be available under (https://michaelbennieufl.github.io/Smackademia-Computational-Linguistics/)[https://michaelbennieufl.github.io/Smackademia-Computational-Linguistics/]


