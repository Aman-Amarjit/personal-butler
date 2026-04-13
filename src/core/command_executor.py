"""
Command Executor

Executes commands safely with permission checking, validation,
and user confirmation for sensitive operations.
"""

import logging
import subprocess
import os
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .command_interpreter import Command, CommandIntent
logger = logging.getLogger(__name__)

# Lazy-loaded game agent (only imported when needed)
_game_agent = None
_auto_player = None
_screen_vision = None

def _get_game_agent():
    global _game_agent
    if _game_agent is None:
        try:
            from src.gaming.game_agent import GameAgent
            _game_agent = GameAgent()
            _game_agent.start()
        except Exception as exc:
            logger.warning(f"Game agent unavailable: {exc}")
    return _game_agent

def _get_auto_player():
    global _auto_player
    if _auto_player is None:
        try:
            from src.gaming.autonomous_player import AutonomousPlayer
            _auto_player = AutonomousPlayer()
        except Exception as exc:
            logger.warning(f"Autonomous player unavailable: {exc}")
    return _auto_player

def _get_screen_vision():
    global _screen_vision
    if _screen_vision is None:
        try:
            from src.gaming.screen_vision import ScreenVision
            _screen_vision = ScreenVision()
        except Exception as exc:
            logger.warning(f"Screen vision unavailable: {exc}")
    return _screen_vision


class ExecutionStatus(Enum):
    """Command execution status"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_CONFIRMATION = "pending_confirmation"
    PERMISSION_DENIED = "permission_denied"
    INVALID_COMMAND = "invalid_command"


@dataclass
class ExecutionResult:
    """Result of command execution"""
    status: ExecutionStatus
    output: str
    error: Optional[str] = None
    requires_confirmation: bool = False


class CommandExecutor:
    """
    Executes commands safely.
    
    Features:
    - System command execution (safe subset)
    - Application launch
    - Information retrieval
    - Permission checking
    - User confirmation for sensitive operations
    """

    def __init__(self):
        """Initialize command executor"""
        # Safe system commands
        self.safe_commands = {
            "shutdown": ["shutdown", "/s", "/t", "60"],
            "restart": ["shutdown", "/r", "/t", "60"],
            "sleep": ["rundll32.exe", "powrprof.dll", "SetSuspendState", "0", "1", "0"],
            "lock": ["rundll32.exe", "user32.dll", "LockWorkStation"],
        }

        # Blocked commands
        self.blocked_commands = [
            "format", "del", "rm", "rmdir", "remove", "uninstall"
        ]

        # Callbacks
        self.on_confirmation_needed: Optional[Callable] = None
        self.on_execution_complete: Optional[Callable] = None

    def execute(self, command: Command) -> ExecutionResult:
        """
        Execute a command.

        Args:
            command: Command to execute

        Returns:
            ExecutionResult with status and output
        """
        try:
            # Validate command
            validation = self._validate_command(command)
            if validation.status != ExecutionStatus.SUCCESS:
                return validation

            # Check if confirmation needed
            if command.requires_confirmation:
                return ExecutionResult(
                    status=ExecutionStatus.PENDING_CONFIRMATION,
                    output="",
                    requires_confirmation=True
                )

            # Execute based on intent
            if command.intent == CommandIntent.APPLICATION_LAUNCH:
                return self._execute_application_launch(command)

            elif command.intent == CommandIntent.SYSTEM_COMMAND:
                return self._execute_system_command(command)

            elif command.intent == CommandIntent.INFORMATION_RETRIEVAL:
                return self._execute_information_retrieval(command)

            elif command.intent == CommandIntent.FILE_OPERATION:
                return self._execute_file_operation(command)

            elif command.intent == CommandIntent.GAME_CONTROL:
                return self._execute_game_control(command)

            elif command.intent == CommandIntent.SING:
                return self._execute_sing(command)

            else:
                return ExecutionResult(
                    status=ExecutionStatus.INVALID_COMMAND,
                    output="",
                    error="Unknown command type"
                )

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                output="",
                error=str(e)
            )

    def _validate_command(self, command: Command) -> ExecutionResult:
        """Validate command for safety"""
        action_lower = command.action.lower()

        # Check blocked commands
        for blocked in self.blocked_commands:
            if blocked in action_lower:
                logger.warning(f"Blocked command attempted: {blocked}")
                return ExecutionResult(
                    status=ExecutionStatus.PERMISSION_DENIED,
                    output="",
                    error=f"Command '{blocked}' is not allowed"
                )

        # Check confidence
        if command.confidence < 0.5:
            return ExecutionResult(
                status=ExecutionStatus.INVALID_COMMAND,
                output="",
                error="Command confidence too low"
            )

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=""
        )

    def _execute_application_launch(self, command: Command) -> ExecutionResult:
        """
        Launch an application by name on Windows.

        Handles:
        - Common desktop apps (notepad, chrome, etc.)
        - Windows Store / UWP apps (whatsapp, spotify, etc.)
        - Website shortcuts (youtube, google, etc.)
        """
        try:
            app_name = command.entities.get("app_name", "").strip().lower()

            if not app_name:
                return ExecutionResult(
                    status=ExecutionStatus.INVALID_COMMAND,
                    output="", error="No application specified"
                )

            # ── 1. Website shortcuts ──────────────────────────────────────
            website_map = {
                "youtube":   "https://youtube.com",
                "google":    "https://google.com",
                "gmail":     "https://mail.google.com",
                "github":    "https://github.com",
                "twitter":   "https://twitter.com",
                "facebook":  "https://facebook.com",
                "instagram": "https://instagram.com",
                "reddit":    "https://reddit.com",
                "netflix":   "https://netflix.com",
                "amazon":    "https://amazon.com",
                "linkedin":  "https://linkedin.com",
                "whatsapp web": "https://web.whatsapp.com",
            }
            for key, url in website_map.items():
                if key in app_name:
                    subprocess.Popen(["start", url], shell=True)
                    return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                          output=f"Opening {key} in browser")

            # ── 2. Windows Store / UWP apps ───────────────────────────────
            # These need `start ms-xxx:` URI or explorer shell: syntax
            uwp_map = {
                "whatsapp":   "whatsapp:",
                "spotify":    "spotify:",
                "calculator": "calculator:",
                "calendar":   "outlookcal:",
                "mail":       "outlookmail:",
                "maps":       "bingmaps:",
                "camera":     "microsoft.windows.camera:",
                "photos":     "ms-photos:",
                "store":      "ms-windows-store:",
                "settings":   "ms-settings:",
                "xbox":       "xbox:",
                "teams":      "msteams:",
                "onenote":    "onenote:",
                "skype":      "skype:",
                "telegram":   "tg:",
                "discord":    "discord:",
                "slack":      "slack:",
                "zoom":       "zoommtg:",
            }
            for key, uri in uwp_map.items():
                if key in app_name:
                    subprocess.Popen(["start", uri], shell=True)
                    logger.info(f"Launched UWP app: {key} via {uri}")
                    return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                          output=f"Opening {key}")

            # ── 3. Common desktop executables ─────────────────────────────
            exe_map = {
                "notepad":        "notepad.exe",
                "paint":          "mspaint.exe",
                "calculator":     "calc.exe",
                "explorer":       "explorer.exe",
                "file explorer":  "explorer.exe",
                "task manager":   "taskmgr.exe",
                "control panel":  "control.exe",
                "command prompt": "cmd.exe",
                "cmd":            "cmd.exe",
                "powershell":     "powershell.exe",
                "word":           "winword.exe",
                "excel":          "excel.exe",
                "powerpoint":     "powerpnt.exe",
                "outlook":        "outlook.exe",
                "chrome":         "chrome.exe",
                "firefox":        "firefox.exe",
                "edge":           "msedge.exe",
                "brave":          "brave.exe",
                "vlc":            "vlc.exe",
                "vs code":        "code.exe",
                "vscode":         "code.exe",
                "visual studio":  "devenv.exe",
                "pycharm":        "pycharm64.exe",
                "steam":          "steam.exe",
                "obs":            "obs64.exe",
            }
            for key, exe in exe_map.items():
                if key in app_name:
                    try:
                        subprocess.Popen(exe)
                        return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                              output=f"Opening {key}")
                    except FileNotFoundError:
                        pass  # fall through to generic launch

            # ── 4. Registry-aware resolution (Stage 3) ───────────────────
            # Query the Windows App Paths registry key for a resolved path
            try:
                from src.core.app_discovery import get_manifest
                manifest = get_manifest()
                resolved = manifest.resolve(app_name, threshold=0.72)
                if resolved:
                    exe_path = manifest.get_exe_path(resolved)
                    if exe_path:
                        try:
                            subprocess.Popen([exe_path])
                            logger.info(f"Registry launch: '{resolved}' → {exe_path}")
                            return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                                   output=f"Opening {resolved}")
                        except Exception:
                            pass
                    # No path but we have a name — try start command
                    try:
                        subprocess.Popen(f'start "" "{resolved}"', shell=True)
                        return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                               output=f"Opening {resolved}")
                    except Exception:
                        pass
            except Exception:
                pass

            # ── 5. Generic fallback ───────────────────────────────────────
            try:
                subprocess.Popen(app_name)
                return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                       output=f"Launched {app_name}")
            except (FileNotFoundError, OSError):
                pass

            # Try via Windows `start` command (searches PATH + registry)
            try:
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
                return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                       output=f"Launched {app_name}")
            except Exception as e:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED, output="",
                    error=f"Could not find or launch '{app_name}': {e}"
                )

        except Exception as e:
            logger.error(f"Error launching application: {e}")
            return ExecutionResult(status=ExecutionStatus.FAILED, output="", error=str(e))

    def _execute_system_command(self, command: Command) -> ExecutionResult:
        """Execute system command"""
        try:
            action_lower = command.action.lower()

            for cmd_name, cmd_args in self.safe_commands.items():
                if cmd_name in action_lower:
                    logger.info(f"Executing system command: {cmd_name}")
                    subprocess.Popen(cmd_args)
                    return ExecutionResult(
                        status=ExecutionStatus.SUCCESS,
                        output=f"Executing {cmd_name}"
                    )

            return ExecutionResult(
                status=ExecutionStatus.INVALID_COMMAND,
                output="",
                error="Unknown system command"
            )

        except Exception as e:
            logger.error(f"Error executing system command: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                output="",
                error=str(e)
            )

    def _execute_information_retrieval(self, command: Command) -> ExecutionResult:
        """Execute information retrieval via Ollama."""
        try:
            query = command.entities.get("query", command.action)
            logger.info(f"Information retrieval query: {query}")

            # Try to answer via Ollama
            try:
                from src.core.ollama_integration import OllamaIntegration
                ollama = OllamaIntegration()
                if ollama.verify_running():
                    answer = ollama.send_request(
                        prompt=query,
                        context="You are PANDA, a helpful AI assistant. Answer concisely.",
                        max_tokens=300,
                    )
                    if answer:
                        return ExecutionResult(
                            status=ExecutionStatus.SUCCESS,
                            output=answer,
                        )
            except Exception as exc:
                logger.warning(f"Ollama unavailable for info retrieval: {exc}")

            # Fallback: return the query echoed back
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=f"I couldn't retrieve information for: {query}. Please ensure Ollama is running.",
            )

        except Exception as e:
            logger.error(f"Error retrieving information: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                output="",
                error=str(e)
            )

    def _execute_file_operation(self, command: Command) -> ExecutionResult:
        """Execute file operation using shutil and os."""
        import shutil

        try:
            operation = command.entities.get("operation", "")
            source = command.entities.get("source", "")
            destination = command.entities.get("destination", "")
            logger.info(f"File operation: {operation} src={source!r} dst={destination!r}")

            if operation == "copy":
                if not source or not destination:
                    return ExecutionResult(
                        status=ExecutionStatus.INVALID_COMMAND,
                        output="",
                        error="copy requires source and destination paths",
                    )
                shutil.copy2(source, destination)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=f"Copied '{source}' to '{destination}'",
                )

            elif operation == "move":
                if not source or not destination:
                    return ExecutionResult(
                        status=ExecutionStatus.INVALID_COMMAND,
                        output="",
                        error="move requires source and destination paths",
                    )
                shutil.move(source, destination)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=f"Moved '{source}' to '{destination}'",
                )

            elif operation == "rename":
                if not source or not destination:
                    return ExecutionResult(
                        status=ExecutionStatus.INVALID_COMMAND,
                        output="",
                        error="rename requires source and destination paths",
                    )
                os.rename(source, destination)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=f"Renamed '{source}' to '{destination}'",
                )

            elif operation == "delete":
                if not source:
                    return ExecutionResult(
                        status=ExecutionStatus.INVALID_COMMAND,
                        output="",
                        error="delete requires a source path",
                    )
                if os.path.isdir(source):
                    shutil.rmtree(source)
                else:
                    os.remove(source)
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    output=f"Deleted '{source}'",
                )

            else:
                return ExecutionResult(
                    status=ExecutionStatus.INVALID_COMMAND,
                    output="",
                    error=f"Unknown file operation: '{operation}'",
                )

        except FileNotFoundError as e:
            logger.error(f"File not found during file operation: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                output="",
                error=f"File not found: {e}",
            )
        except Exception as e:
            logger.error(f"Error executing file operation: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                output="",
                error=str(e)
            )

    def _execute_sing(self, command: Command) -> ExecutionResult:
        """Pick a fun song and return the lyrics for TTS to sing."""
        import random
        songs = [
            (
                "Twinkle Twinkle Little Star",
                "Twinkle twinkle little star, how I wonder what you are! "
                "Up above the world so high, like a diamond in the sky. "
                "Twinkle twinkle little star, how I wonder what you are!"
            ),
            (
                "Happy Birthday",
                "Happy birthday to you! Happy birthday to you! "
                "Happy birthday dear friend, happy birthday to you!"
            ),
            (
                "Row Your Boat",
                "Row row row your boat, gently down the stream. "
                "Merrily merrily merrily merrily, life is but a dream!"
            ),
            (
                "PANDA's Song",
                "I am PANDA, your AI friend, here to help until the end! "
                "Ask me anything you need, I will help you guaranteed! "
                "PANDA PANDA, that is me, the best assistant you will see!"
            ),
            (
                "Old MacDonald",
                "Old MacDonald had a farm, E-I-E-I-O! "
                "And on his farm he had a cow, E-I-E-I-O! "
                "With a moo moo here and a moo moo there, "
                "here a moo, there a moo, everywhere a moo moo! "
                "Old MacDonald had a farm, E-I-E-I-O!"
            ),
        ]
        title, lyrics = random.choice(songs)
        logger.info(f"Singing: {title}")
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=f"♪ {lyrics} ♪",
        )

    def _execute_game_control(self, command: Command) -> ExecutionResult:
        """Route game control commands to the GameAgent, ScreenVision, or AutonomousPlayer."""
        try:
            entities = command.entities
            game_cmd = entities.get("game_command", command.action)

            # ── Autonomous play ───────────────────────────────────────────
            if "auto_play" in entities:
                return self._handle_auto_play(entities["auto_play"])

            # ── Screen vision query ───────────────────────────────────────
            if "vision_query" in entities:
                return self._handle_vision_query(entities["vision_query"])

            # ── Force profile switch ──────────────────────────────────────
            if "force_game" in entities:
                agent = _get_game_agent()
                if agent is None:
                    return ExecutionResult(status=ExecutionStatus.FAILED,
                                          output="", error="Game agent not available")
                game_name = entities["force_game"]
                ok = agent.force_profile(game_name)
                if ok:
                    return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                          output=f"Switched to game profile: {game_name}")
                return ExecutionResult(status=ExecutionStatus.FAILED, output="",
                                       error=f"Unknown game profile: {game_name}")

            # ── Direct key control ────────────────────────────────────────
            if "key" in entities:
                agent = _get_game_agent()
                if agent is None:
                    return ExecutionResult(status=ExecutionStatus.FAILED,
                                          output="", error="Game agent not available")
                key    = entities["key"]
                action = entities.get("key_action", "press")
                result = agent.execute_key(key, hold=(action == "hold"))
                return ExecutionResult(status=ExecutionStatus.SUCCESS, output=result)

            # ── Voice command → macro ─────────────────────────────────────
            agent = _get_game_agent()
            if agent:
                result = agent.handle_voice_command(game_cmd)
                if result:
                    return ExecutionResult(status=ExecutionStatus.SUCCESS, output=result)

            return ExecutionResult(status=ExecutionStatus.INVALID_COMMAND, output="",
                                   error=f"No game action matched: '{game_cmd}'")

        except Exception as exc:
            logger.error(f"Game control error: {exc}")
            return ExecutionResult(status=ExecutionStatus.FAILED, output="", error=str(exc))

    def _handle_vision_query(self, query: str) -> ExecutionResult:
        """Answer a question about the current screen."""
        vision = _get_screen_vision()
        if vision is None:
            return ExecutionResult(status=ExecutionStatus.FAILED, output="",
                                   error="Screen vision not available")
        try:
            lower = query.lower()
            if "what game" in lower:
                answer = vision.what_game()
            elif "read" in lower or "text" in lower:
                answer = vision.read_text()
            elif "game state" in lower or "what should" in lower:
                answer = vision.game_state()
            else:
                answer = vision.ask(query)
            return ExecutionResult(status=ExecutionStatus.SUCCESS, output=answer)
        except Exception as exc:
            return ExecutionResult(status=ExecutionStatus.FAILED, output="", error=str(exc))

    def _handle_auto_play(self, action: str) -> ExecutionResult:
        """Start, stop, pause, or resume autonomous play."""
        player = _get_auto_player()
        if player is None:
            return ExecutionResult(status=ExecutionStatus.FAILED, output="",
                                   error="Autonomous player not available")
        if action == "start":
            player.start()
            return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                   output="Autonomous play started. I'll play for you!")
        elif action == "stop":
            player.stop()
            return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                   output="Autonomous play stopped.")
        elif action == "pause":
            player.pause()
            return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                   output="Autonomous play paused.")
        elif action == "resume":
            player.resume()
            return ExecutionResult(status=ExecutionStatus.SUCCESS,
                                   output="Autonomous play resumed.")
        return ExecutionResult(status=ExecutionStatus.INVALID_COMMAND, output="",
                               error=f"Unknown auto_play action: {action}")

    def confirm_execution(self, command: Command) -> ExecutionResult:
        """
        Execute command after user confirmation.

        Args:
            command: Command to execute

        Returns:
            ExecutionResult
        """
        logger.info("User confirmed command execution")
        return self.execute(command)

    def get_status(self) -> Dict[str, Any]:
        """Get executor status"""
        return {
            "safe_commands": list(self.safe_commands.keys()),
            "blocked_commands": self.blocked_commands
        }
