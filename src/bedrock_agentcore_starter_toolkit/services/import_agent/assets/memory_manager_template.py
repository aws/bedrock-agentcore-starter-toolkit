# pylint: disable=line-too-long
"""Long Term Memory Manager for generated agents.

This module provides a custom memory manager that mimics the functionality of Bedrock Agents
Long Term Memory and Sessions.
"""

import asyncio
import json
import os
import weakref
from datetime import datetime
from typing import Any, Dict, List, Set


class LongTermMemoryManager:
    """Custom Memory Manager to have equivalent functionality with Bedrock Agents Long Term Memory and Sessions."""

    # Class variable to keep track of all instances
    _instances: Set[weakref.ref] = set()

    def __init__(
        self,
        llm_summarizer,
        storage_path: str = "output",
        max_sessions: int = 10,
        summarization_prompt: str = None,
        max_days: int = 30,
        platform: str = "langchain",
    ):
        """Initialize the LongTermMemoryManager."""
        self.llm_summarizer = llm_summarizer
        self.storage_path = storage_path
        self.max_sessions = max_sessions
        self.max_days = max_days
        self.current_session_messages = []
        self.summarization_prompt = summarization_prompt
        self._last_memory_update_time = 0
        self.platform = platform
        self._session_ended = False  # Track if this instance has ended its session

        self.session_summaries = self._load_session_summaries()

        # Register this instance in the class-level instances set
        self._instances.add(weakref.ref(self, self._cleanup_reference))

    @staticmethod
    def _cleanup_reference(ref):
        """Callback for when a weak reference is removed."""
        LongTermMemoryManager._instances.discard(ref)

    def _load_session_summaries(self) -> List[Dict[str, Any]]:
        """Load all stored session summaries."""
        summary_file = self.storage_path
        if os.path.exists(summary_file):
            with open(summary_file, "r") as f:
                return json.load(f)
        return []

    def _save_session_summaries(self):
        summary_file = self.storage_path
        with open(summary_file, "a+", encoding="utf-8") as f:
            f.truncate(0)
            json.dump(self.session_summaries, f)
        self._last_memory_update_time = datetime.now().timestamp()

    def add_message(self, message: Dict[str, str]):
        """Add a message to the current session."""
        self.current_session_messages.append(message)

    def _generate_session_summary(self) -> str:
        try:
            conversation_str = "\n\n".join(
                [f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.current_session_messages]
            )

            past_summaries = "\n".join([summary["summary"] for summary in self.session_summaries])

            summarization_prompt = self.summarization_prompt.replace(
                "$past_conversation_summary$", past_summaries
            ).replace("$conversation$", conversation_str)

            if self.platform == "langchain":
                summary_response = self.llm_summarizer.invoke(summarization_prompt).content
            else:

                def inference(model, messages, system_prompt=""):
                    async def run_inference():
                        results = []
                        async for event in model.stream(messages=messages, system_prompt=system_prompt):
                            results.append(event)
                        return results

                    response = asyncio.run(run_inference())

                    text = ""
                    for chunk in response:
                        if "contentBlockDelta" not in chunk:
                            continue
                        text += chunk["contentBlockDelta"].get("delta", {}).get("text", "")

                    return text

                summary_response = inference(
                    self.llm_summarizer, messages=[{"role": "user", "content": [{"text": summarization_prompt}]}]
                )

            return summary_response
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            message = self.current_session_messages[-1]["content"] if self.current_session_messages else "No messages"
            return f"Session summary generation failed. Last message: {message}"

    @classmethod
    def _cleanup_instance(cls):
        """Remove dead references from the instances set."""
        cls._instances = {ref for ref in cls._instances if ref() is not None}

    @classmethod
    def get_active_instances_count(cls):
        """Return the number of active memory manager instances."""
        # Clean up any dead references first
        cls._instances = {ref for ref in cls._instances if ref() is not None}
        return len(cls._instances)

    @classmethod
    def get_active_instances(cls):
        """Return a list of all active memory manager instances."""
        # Clean up any dead references first
        cls._instances = {ref for ref in cls._instances if ref() is not None}
        return [ref() for ref in cls._instances if ref() is not None]

    @classmethod
    def end_all_sessions(cls):
        """End sessions for all active memory manager instances.

        This is a convenience method that can be called from anywhere to end all sessions.
        """
        instances = cls.get_active_instances()
        if instances:
            instances[0].end_session()

    def end_session(self):
        """End the current session and trigger end_session for all other instances.

        This ensures that when one agent ends its session, all other agents do the same.
        """
        # Prevent recursive calls
        if self._session_ended:
            return

        self._session_ended = True

        # Process this instance's session
        if self.current_session_messages:
            summary = self._generate_session_summary()
            session_summary = {"timestamp": datetime.now().isoformat(), "summary": summary}
            self.session_summaries.append(session_summary)

            self.session_summaries = [
                summary
                for summary in self.session_summaries
                if (
                    datetime.fromisoformat(session_summary["timestamp"]) - datetime.fromisoformat(summary["timestamp"])
                ).days
                <= self.max_days
            ]

            if len(self.session_summaries) > self.max_sessions:
                self.session_summaries = self.session_summaries[-self.max_sessions :]

            self._save_session_summaries()

            self.current_session_messages = []

        # End sessions for all other instances
        for instance_ref in list(self._instances):
            instance = instance_ref()
            if instance is not None and instance is not self and not instance._session_ended:
                try:
                    instance.end_session()
                except Exception as e:
                    print(f"Error ending session for another instance: {str(e)}")

        # Reset the flag so this instance can be used again if needed
        self._session_ended = False

    def get_memory_synopsis(self) -> str:
        """Get a synopsis of the memory, including all session summaries."""
        return "\n".join([summary["summary"] for summary in self.session_summaries])

    def has_memory_changed(self) -> bool:
        """Check if the memory has changed since the last update."""
        summary_file = self.storage_path

        if not os.path.exists(summary_file):
            return False

        current_mtime = os.path.getmtime(summary_file)
        if current_mtime != self._last_memory_update_time:
            self._last_memory_update_time = current_mtime
            return True
        return False

    def clear_current_session(self):
        """Clear the current session messages."""
        self.current_session_messages = []
