import typer
from rich import print
from typing import Optional
from pathlib import Path

#Default import to globally enable/disable debugger
from template_python.debugger import *  
ic.configureOutput(prefix=f'{Path(__file__).name} -> ')

app = typer.Typer()

@app.command()
def template_fn(
    template_str: str, 
    template_bool: bool = False):
    """This is a sample function to be executed through the cli app
    """
    ic(template_bool)
    ic(template_str)

