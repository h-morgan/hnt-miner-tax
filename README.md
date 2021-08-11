# Helium Miner Tax Tool 

This tool is a cli tool that can be run to determine a Helium miner's rewards income in USD for a requested tax year. 

Once initial setup is complete, to run the tool you need to give it a user's Helium wallet address and the tax year of interest. Additional instructions are included below.

## Setup 

First, clone the repository onto your machine:
```bash
git clone git@github.com:h-morgan/hnt-miner-tax.git
```
Then move into the cloned repository on your local machine, and perform the following commands there.

Next, initialize a virtual environment using venv. Ensure you are using python3:
```bash
python3 -m venv venv
```

Once you have your virtual environment initalized, next step is to activate it:
```bash
source venv/bin/activate
```

Now that its activated, we need to install the required packages:
```bash
pip install -r requirements.txt
```
Note: you will only need to intialize a venv and install the required packages one time upon setup. From here on out, you will only need to ensure the venv is activated and you will be able to run the tool.

## How to run
To run this tool, you will need a Helium wallet address and the tax year you are interested in. Once you have that, you can pass those two pieces of information as arguments to the cli tool one of two ways: via cli arguments, or input arguments.

### CLI Arguments

To run the tool with the wallet address and tax year as inline cli arguments, it looks like this:
```bash
```