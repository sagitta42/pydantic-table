import enum
import inspect
import logging
from pathlib import Path
from typing import Any
from dotenv import dotenv_values


class AnsiStyle(str, enum.Enum):
    normal = "0"
    bold = "1"
    start = "\033["
    end = "\033[0m"

    def __str__(self) -> str:
        return self.value


class AnsiColor(str, enum.Enum):
    green = "32"
    grey = "90"
    red = "31"
    yellow = "33"
    white = "37"

    def apply(self, message: Any, bold: bool = False) -> str:
        """
        To be used with color based
        """
        style = AnsiStyle.bold if bold else AnsiStyle.normal
        ret = f"{AnsiStyle.start}{style};{self.value}m{message}{AnsiStyle.end}"
        return ret

    def bold(self, message: Any) -> str:
        """
        Shortcut for bold colored text
        """
        ret = self.apply(message, bold=True)
        return ret

    def __str__(self) -> str:
        return self.value


class LevelFormatter(logging.Formatter):
    def __init__(self, formats, default_fmt=None, datefmt=None):
        super().__init__(datefmt=datefmt)
        self.formats = {
            level: logging.Formatter(fmt, datefmt=datefmt)
            for level, fmt in formats.items()
        }
        self.default_formatter = logging.Formatter(
            default_fmt or "%(message)s", datefmt=datefmt
        )

    def format(self, record):
        formatter = self.formats.get(record.levelno, self.default_formatter)
        return formatter.format(record)


class Logger:
    def __init__(self, log_level=logging.INFO):
        self._logger = logging.getLogger(__name__)

        full_format = "%(asctime)s [%(levelname)s] %(classname)s.%(funcName)s:%(lineno)d - %(message)s"
        short_format = "[%(levelname)s] %(classname)s - %(message)s"
        no_format = ""
        level_format = full_format if log_level == logging.DEBUG else no_format
        formatter = LevelFormatter(
            {
                logging.DEBUG: full_format,
                logging.ERROR: level_format,
                logging.INFO: level_format,
                logging.WARNING: level_format,
            }
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        self._logger.addHandler(handler)

        self._logger.setLevel(log_level)
        self._logger.propagate = False

    def info(self, message: Any, header: bool = False):
        color = AnsiColor.green if header else AnsiColor.white
        return self._log(logging.INFO, color.apply(message, header))

    def error(self, message: Any):
        return self._log(logging.ERROR, AnsiColor.red.apply(message))

    def warning(self, message: Any, important: bool = False):
        if important:
            message = f"! WARNING ! {message}"
        return self._log(logging.WARNING, AnsiColor.yellow.apply(message, important))

    def debug(self, message: Any):
        return self._log(logging.DEBUG, AnsiColor.grey.apply(message))

    def _log(self, level, message: Any):
        """
        Common log interface for info/error/warning/debug.

        Auto-detect class name of caller.
        Account for stack level to display correct funcName and lineno.
            Skip 2 stack levels including this method,
            the info/error/warning/debug method calling it,
        """
        self._logger.log(
            level,
            message,
            extra={"classname": self._get_caller_class_name()},
            stacklevel=3,
        )

    def _get_caller_class_name(self):
        """
        Determine class name of where logger is called from.

        Obtain frame index 3 corresponding to actual caller
            (0 = this method, 1 = _log internal method, 2 = info/warning/error/debug logger call).
        Return class or module name of that frame.
        """
        frame = inspect.stack()[3].frame
        if "self" in frame.f_locals:
            return type(frame.f_locals["self"]).__name__
        elif "cls" in frame.f_locals:
            return frame.f_locals["cls"].__name__
        return frame.f_globals.get("__name__", "-")


# NOTE: dotenv_values() in some cases yielded empty .env for unexplained reason
env_config = dotenv_values(Path.cwd() / ".env")
is_debug = env_config.get("DEBUG_PYDANTIC_TABLE", "").lower() in ("true", "1")
logg = Logger(log_level=logging.DEBUG if is_debug else logging.INFO)
