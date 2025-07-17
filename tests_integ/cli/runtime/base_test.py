import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, List

from click.testing import Result
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.cli import app

logger = logging.getLogger("cli-runtime-base-test")


@dataclass
class CommandInvocation:
    command: List[str]
    user_input: List[str]
    validator: Callable[[Result], Any]


class BaseCLIRuntimeTest(ABC):
    """
    Base class for CLI runtime tests.
    This class can be extended to create specific CLI runtime E2E test cases.
    """

    def run(self, tmp_path) -> None:
        """
        Run the simple agent CLI test.
        This method should implement the logic to execute the test.
        """
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            runner = CliRunner()

            self.setup()
            command_invocations = self.get_command_invocations()

            for command_invocation in command_invocations:
                command = command_invocation.command
                input = command_invocation.user_input
                validator = command_invocation.validator

                logger.info("Running command %s with input %s", command, input)

                with create_pipe_input() as pipe_input:
                    with create_app_session(input=pipe_input):
                        for data in input:
                            pipe_input.send_text(data + "\n")

                        result = runner.invoke(app, args=command)

                validator(result)
        finally:
            os.chdir(original_dir)

    def setup(self) -> None:
        # base implementation
        return

    @abstractmethod
    def get_command_invocations(self) -> List[CommandInvocation]:
        """
        Get the commands to be tested.
        This method should be implemented by subclasses to return the specific commands.
        """
        pass
