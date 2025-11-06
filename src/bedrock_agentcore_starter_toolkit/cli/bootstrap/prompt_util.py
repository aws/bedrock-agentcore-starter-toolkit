from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from ...cli.common import console

def prompt_choice_until_valid_input(label: str, choices: list[str]) -> str:
    completer = WordCompleter(choices, ignore_case=True)
    while True:
        entered = prompt(f"{label} ({'/'.join(choices)}): ", completer=completer).strip()
        # accept any cased input
        for choice in choices:
            if choice.lower() == entered.lower():
                return choice
        console.print(f"[yellow]Invalid choice. Please enter one of: {', '.join(choices)}[/yellow]")

def prompt_confirm_continue(warn_str: str) -> bool:
    response = prompt(HTML(f"<ansiyellow><b>⚠ {warn_str}: Do you want to continue [y/N]: </b></ansiyellow>")).strip()
    return response.lower() in {"y", "yes"}
